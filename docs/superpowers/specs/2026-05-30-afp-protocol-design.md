# AFP — Agent Feedback Protocol

**Documento de diseño** · v0.2.1 · 2026-05-30

> **Changelog v0.2 → v0.2.1** (ajustes de precisión tras 2ª review):
> - El Harvester ya no descarta `fault_domain ≠ tool`; los conserva como señales
>   de docs/contrato/UX.
> - Corregido "~8 campos" → "10 campos" (el core tiene 10).
> - Retórica de `fault_domain` suavizada: "dónde parece estar la causa" en vez de
>   "de quién es la culpa" (el nombre del campo no cambia).
>
> **Changelog v0.1 → v0.2** (tras review externa de GPT-5.5):
> - `tool_anchor` reemplazado por `subject_uri` apoyado en **PURL (ECMA-427)**.
> - Esquema partido en **core (required)** + **extensiones (optional)** para no inflar el MVP.
> - Nuevo eje **`fault_domain`** que separa fricción de culpa (no toda fricción es culpa de la tool).
> - Cascada de descubrimiento endurecida: **sin manifiesto, nunca se auto-envía**; solo `local` spool o borrador con confirmación humana.
> - Nueva **§ clasificación y minimización de PII** (la redacción no se limita a `inputs`).
> - Nuevo **threat model** (§).
> - **Bridge con OpenTelemetry** (`trace_id` + relación complementaria, no opuesta).
> - Camino a spec **normativa** (RFC 2119 + JSON Schema + test vectors) marcado como Fase 1.5.

---

## 1. Resumen ejecutivo

A medida que más sistemas del mundo se diseñan para que agentes de IA (LLMs)
ejecuten herramientas sobre ellos —vía MCP, CLIs, skills, APIs, plugins de
GUI, etc.—, falta un canal estándar para que esos agentes **devuelvan
información sobre la fricción que encuentran al usar esas herramientas**.

Hoy un agente que tropieza con un bug, un comportamiento no documentado o una
capacidad ausente simplemente improvisa, falla o avisa al usuario, y ese
conocimiento se pierde. AFP define **el camino de vuelta** que le falta a
protocolos como MCP: una forma canónica y agnóstica al transporte de que un
agente deje un "parte de campo" (*field report*) dirigido a la herramienta que
usó, para que los agentes que mantienen y mejoran esa herramienta sepan **dónde,
cómo y por qué** fallaron otros agentes al usarla.

El efecto buscado es un **ecosistema de información de uso**: cada agente del
mundo, sin proponérselo, se convierte en un tester de caja negra que escribe
bug reports en lenguaje de producto, alimentando un bucle de auto-mejora de las
herramientas impulsado por uso real.

### Qué es AFP (y qué no es)

- **Es un estándar** (un acuerdo escrito), en la misma familia que MCP o
  Agent-to-Agent. No es propiedad de nadie y cualquiera puede implementarlo sin
  pedir permiso.
- **Es agnóstico al tipo de herramienta.** El protocolo no sabe ni le importa
  si la tool era un MCP, un comando de terminal, una skill, una API o un plugin
  de GUI con clics.
- **Es agnóstico al harness.** Funciona igual desde Claude Code, Cursor, Cline,
  Aider o cualquier otro entorno agéntico.
- **Es complementario a la telemetría, no un sustituto.** OpenTelemetry (semconv
  GenAI) traza *ejecuciones*; Sentry reporta *excepciones técnicas*. AFP captura
  algo que ninguno de los dos modela: la **intención frustrada** —qué quería
  lograr el agente, qué esperaba de la tool, y por qué su plan se rompió—. Un
  field report puede **derivarse de** un trace OTel y enlazarse a él
  (`trace_id`), pero no lo reemplaza.

### Posicionamiento frente a estándares existentes

| Estándar | Qué resuelve | Qué NO resuelve (hueco de AFP) |
|----------|--------------|-------------------------------|
| **MCP** | Exponer e invocar tools (nombre, descripción, input schema). | Canal de feedback hacia el mantenedor de la tool. |
| **A2A** | Comunicación agente-agente, discovery por Agent Cards. | Reportes de fricción de uso. |
| **OpenTelemetry GenAI / OWASP AOS** | Trazar ejecuciones y spans de agentes. | Convertir intención frustrada en feedback mantenible. |
| **PURL (ECMA-427)** | Identificar paquetes de forma universal. | (AFP lo **reutiliza**, no compite.) |

### Principio rector

> El centro del protocolo no es el transporte, es **el dato**. Si el field
> report y la identidad de la tool están bien definidos, el transporte y el
> consumidor del dato son intercambiables. Y siempre que sea posible, **nos
> apoyamos en estándares existentes (PURL, OTel) en vez de reinventarlos**.

---

## 2. Arquitectura general

AFP se compone de **cuatro piezas separadas y apilables**. Cada una se entiende,
se construye y se prueba de forma independiente.

```
┌─────────────────────────────────────────────────────────────┐
│  1. EL DATO — "Field Report"                                  │
│     Esquema universal y agnóstico al transporte.              │
│     Core required (mínimo) + extensiones optional.            │
│     Captura: intención, plan, expectativa, qué pasó, causa.   │
│     Es el corazón. Todo lo demás sirve a esto.                │
├─────────────────────────────────────────────────────────────┤
│  2. LA IDENTIDAD — "subject_uri"                              │
│     Identificador único y determinista, apoyado en PURL.      │
│     Funciona para MCP, CLI, skill, API, GUI, lo que sea.      │
│     Capa 1: manifiesto declarado (afp.json) → opt-in.         │
│     Capa 2: inferencia → SOLO local/draft, nunca auto-envío.  │
├─────────────────────────────────────────────────────────────┤
│  3. EL TRANSPORTE — "Sinks"                                   │
│     Por dónde viaja el reporte hasta su casa.                 │
│     Sinks remotos = opt-in del mantenedor. El dato es igual.  │
├─────────────────────────────────────────────────────────────┤
│  4. EL BUCLE — "Harvester"                                    │
│     Agente-mantenedor que lee, deduplica, prioriza y abre     │
│     issues/PRs de mejora. NO es parte del estándar:           │
│     es UN consumidor del estándar.                            │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de punta a punta

1. Un agente (en cualquier harness) usa una herramienta y su **plan se rompe**.
2. Genera un **Field Report** (pieza 1): qué quería, qué esperaba, qué recibió,
   en qué punto del plan se rompió, y **dónde parece estar la causa**
   (`fault_domain`).
3. Resuelve la **identidad** de la tool (pieza 2): `subject_uri` + buzón.
4. **Si hay `afp.json`**, deposita por el transporte declarado (pieza 3). **Si
   no**, lo guarda en spool local o como borrador para revisión humana — nunca
   se auto-envía a un repo que no lo pidió.
5. Más tarde, el **Harvester** del dueño (pieza 4) recoge, agrupa, prioriza y
   genera trabajo de mejora real.

### Frontera del estándar

El **estándar** son las piezas **1, 2 y el formato del transporte (3)**. El
**Harvester (4) NO es el estándar** — es *un* consumidor de él. Pueden existir
muchos Harvesters distintos y todos funcionan porque hablan el mismo formato,
igual que mil navegadores distintos hablan HTTP.

---

## 3. Pieza 1 — El Field Report (el dato)

Regla de oro: **captura la intención frustrada, no el error técnico.**

El esquema se parte en **core (required)** —el mínimo válido, barato de
generar— y **extensiones (optional)** —enriquecen el reporte cuando hay
contexto disponible—. El core son 10 campos baratos de generar; el resto es
opcional.

### 3.1 Core (required)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `schema_version` | string | Versión del esquema, ej. `afp/0.2`. |
| `report_id` | string | Identificador único del reporte. |
| `subject_uri` | string (URI) | Identidad única de la herramienta (ver §4). |
| `goal` | string | Qué intentaba lograr el agente, en lenguaje de producto. |
| `expectation` | string | Qué esperaba que devolviera/hiciera la tool. |
| `observed` | string | Qué recibió/ocurrió en realidad. |
| `friction_type` | enum | Qué tipo de fricción fue (§3.3). |
| `fault_domain` | enum | Dónde parece estar la causa de la fricción (§3.4). **No toda fricción se origina en la tool.** |
| `severity` | enum | `blocked` \| `degraded` \| `cosmetic`. |
| `timestamp` | string (ISO 8601) | Cuándo ocurrió. |

### 3.2 Extensiones (optional)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `tool_version` | string | Versión observada de la tool. Sin esto el mantenedor no sabe si ya lo arregló. |
| `plan_step` | string | En qué punto de su plan estaba. Ej: "Paso 3 de 5". |
| `workaround` | string | Si encontró una salida, cuál. (Sugiere el fix.) |
| `inputs_redacted` | object | Argumentos usados, redactados (§5). |
| `harness` | string | Entorno agéntico (`claude-code`, `cursor`, `cline`, `aider`…). |
| `harness_version` | string | Versión del harness. |
| `agent_model` | string | Modelo que generó el reporte (ej. `claude-opus-4.8`). |
| `tool_call_name` | string | Nombre concreto de la llamada/sub-herramienta invocada. |
| `tool_call_id` | string | ID de la invocación, si el harness lo provee. |
| `trace_id` | string | **Bridge OTel**: enlaza con la traza de la que se deriva este reporte. |
| `contract_ref` | string | Referencia al contrato/schema que se esperaba cumplir. |
| `evidence` | array | Fragmentos (redactados) que respaldan el reporte. |
| `confidence` | enum | `high` \| `medium` \| `low`: cuán seguro está el agente de su diagnóstico. |
| `reproducibility` | enum | `deterministic` \| `intermittent` \| `once`. |
| `dedupe_key` | string | Clave de agrupación sugerida (si se omite, el Harvester la deriva). |

### 3.3 `friction_type` — qué tipo de fricción (enum cerrado)

- `bug` — la tool falla de forma demostrable.
- `undocumented_behavior` — funciona, pero de forma no documentada/sorprendente.
- `missing_capability` — falta una capacidad que el plan necesitaba.
- `confusing_interface` — la interfaz/contrato indujo a error.
- `wrong_output` — devolvió algo incorrecto o en formato inesperado.
- `integration_mismatch` — falla al integrarse con el resto del sistema u otras tools.

### 3.4 `fault_domain` — dónde parece estar la causa (enum cerrado)

Eje **separado** de `friction_type`. Indica el **dominio probable** de la
fricción, sin emitir un juicio definitivo de culpa. Evita que el protocolo asuma
que cualquier fallo del agente se origina en la tool. Un mantenedor confía mucho
más en un flujo de reportes que sabe distinguir su propio bug de un mal uso del
agente.

- `tool` — la herramienta se comportó mal.
- `agent_misuse` — el agente la usó incorrectamente (input mal formado, orden equivocado).
- `ambiguous_contract` — el contrato era ambiguo; culpa compartida tool↔agente.
- `environment_issue` — fallo del entorno (red, dependencias, permisos del sistema).
- `permission_denied` — faltaban permisos/credenciales.
- `rate_limit` — limitación de tasa del proveedor.
- `timeout` — expiró sin respuesta.

### 3.5 Universalidad del esquema (prueba de fuego)

El mismo esquema, **sin añadir ni quitar campos**, sirve para cualquier tipo de
herramienta. Lo único que cambia es el `subject_uri` (ver §4).

```json
// CLI (subject_uri usa PURL)
{ "schema_version": "afp/0.2", "report_id": "afp_01H...",
  "subject_uri": "pkg:npm/eslint@9.2.0",
  "goal": "Auto-arreglar problemas de lint antes de commitear",
  "expectation": "--fix corregiría las comillas y saldría con código 0",
  "observed": "Salió con código 1 sin explicar qué regla no era auto-fixable",
  "friction_type": "confusing_interface", "fault_domain": "tool",
  "severity": "degraded", "timestamp": "2026-05-30T18:00:00Z",
  "plan_step": "3/6 — limpiar antes de los tests",
  "workaround": "Parseé el stdout a mano", "harness": "claude-code" }

// Skill
{ "schema_version": "afp/0.2", "report_id": "afp_01H...",
  "subject_uri": "afp:skill/superpowers/test-driven-development",
  "goal": "Aplicar TDD a un bugfix en una base sin tests previos",
  "expectation": "Cubriría el caso de codebase sin framework de test",
  "observed": "Asume que ya existe un test runner; no dice qué hacer si no hay",
  "friction_type": "missing_capability", "fault_domain": "tool",
  "severity": "blocked", "timestamp": "2026-05-30T18:01:00Z",
  "workaround": "Configuré pytest por mi cuenta", "harness": "claude-code" }

// API REST (fault_domain distingue culpa)
{ "schema_version": "afp/0.2", "report_id": "afp_01H...",
  "subject_uri": "https://api.stripe.com/v1/charges",
  "goal": "Crear un cargo de prueba en sandbox",
  "expectation": "Un error claro si falta el campo 'currency'",
  "observed": "Devolvió 400 con un mensaje genérico que no nombra el campo",
  "friction_type": "wrong_output", "fault_domain": "ambiguous_contract",
  "severity": "degraded", "timestamp": "2026-05-30T18:02:00Z",
  "inputs_redacted": { "amount": "[REDACTED]" }, "harness": "aider",
  "trace_id": "otel-4bf92f3577b34da6a3ce929d0e0e4736" }
```

---

## 4. Pieza 2 — Identidad y descubrimiento (`subject_uri`)

### 4.1 Nombrar la tool de forma única (`subject_uri`)

**Apoyado en estándares existentes.** AFP no inventa un esquema de nombres
nuevo donde ya existe uno; **extiende PURL** y reutiliza URIs nativas:

| Tipo de tool | `subject_uri` | Base |
|--------------|---------------|------|
| Paquete (CLI/lib) | `pkg:npm/eslint@9.2.0` · `pkg:pypi/ruff` | **PURL / ECMA-427** |
| API HTTP | `https://api.stripe.com/v1/charges` | URL nativa |
| Servidor MCP | `mcp://github.com/user/repo#tool_name` | esquema MCP |
| Skill | `afp:skill/namespace/nombre` | esquema propio (no hay estándar previo) |
| GUI / plugin | `afp:app/plataforma/plugin` | esquema propio |
| Binario opaco | `afp:bin/sha256:<hash>` | último recurso |

**Requisito clave:** el `subject_uri` es **determinista** — dos agentes
distintos, en harness distintos, usando la misma tool generan el **mismo URI**.
Sin esto, el Harvester no puede agrupar.

### 4.2 Descubrir el buzón (cascada endurecida)

```
Capa 1 (preferente): MANIFIESTO DECLARADO — "afp.json"  → OPT-IN
  La tool publica un fichero estándar que declara su buzón y esquema.
  → MCP:    en su capability/metadata.
  → CLI:    campo en package.json / pyproject.toml.
  → Repo:   /.well-known/afp.json o /afp.json en la raíz.
  → Skill:  campo en el frontmatter de la skill.
  Solo aquí se permiten sinks REMOTOS (issues, http).

Capa 2 (fallback): SIN MANIFIESTO  → NUNCA AUTO-ENVÍO
  Si no hay afp.json, el agente puede resolver la identidad por inferencia
  (campo "bugs"/"repository", git remote, host de la API) PERO:
    - NO abre issues ni hace POST a nadie.
    - Guarda el reporte en SPOOL LOCAL, o
    - genera un BORRADOR que requiere confirmación humana explícita
      antes de enviarse a ningún sitio.
```

> **Por qué este endurecimiento (cambio clave de v0.2):** auto-abrir issues en
> repos que no han adoptado AFP se percibe como **spam automatizado de agentes**
> y es un vector de abuso. La adopción remota debe ser siempre **opt-in del
> mantenedor** vía `afp.json`. La inferencia sigue dando valor (el reporte se
> genera y se encola), pero el envío a terceros nunca es automático.

> **Descartado del núcleo (YAGNI):** un "sumidero comunitario" central se
> consideró y se descartó: rompe la descentralización e introduce gobernanza,
> coste, spam, poisoning y confianza que ninguna otra pieza tiene. Posible
> extensión futura opcional de la que el protocolo **no depende**.

### 4.3 Formato del manifiesto `afp.json`

```json
{
  "afp_version": "0.2",
  "subject_uri": "mcp://github.com/user/nadir-astro",
  "sink": { "type": "github_issues", "repo": "user/nadir-astro", "label": "afp-report" },
  "redaction": "required",
  "accepts_remote": true,
  "schema_extensions": []
}
```

---

## 5. Privacidad: clasificación y minimización de datos

La redacción **no se limita** a `inputs_redacted`. Campos de texto libre como
`goal`, `observed`, `workaround` y `plan_step` también pueden filtrar datos
sensibles. El protocolo exige **minimización de datos por defecto**.

### 5.1 Clasificación de campos

| Clase | Significado | Tratamiento |
|-------|-------------|-------------|
| **público** | Seguro para repos públicos (`friction_type`, `severity`, `subject_uri`…). | Se envía tal cual. |
| **privado** | Puede contener detalles operativos (`harness`, `tool_call_name`). | Se envía solo a sinks privados o con consentimiento. |
| **sensible** | Texto libre que puede contener PII (`goal`, `observed`, `workaround`, `inputs_redacted`). | **Redacción obligatoria** antes de enviar. |
| **prohibido** | Nunca se incluye (secretos, tokens, credenciales, PII directa). | Filtrado duro; si se detecta, se aborta el envío. |

### 5.2 Reglas

1. **Redacción obligatoria** de la clase *sensible* antes de cualquier envío
   (`"redaction": "required"` en `afp.json` lo refuerza).
2. **Filtrado duro** de la clase *prohibido*: detección de secretos/PII; si se
   detecta, el reporte no se envía.
3. **Minimización por defecto**: el agente incluye lo mínimo necesario para que
   el reporte sea accionable, no todo el contexto disponible.
4. Es el **principal riesgo legal** del proyecto y una decisión de diseño.

---

## 6. Pieza 3 — Transporte (Sinks)

No se inventa canal nuevo; se reutilizan los existentes. El `afp.json` declara
cuál. **Los sinks remotos requieren opt-in del mantenedor.** El dato es
idéntico; solo cambia el sobre.

| Tipo de sink | Comportamiento | Requiere `afp.json` | Estado |
|--------------|----------------|---------------------|--------|
| `local` | Spool en carpeta local (`.afp/reports.jsonl`). | No | v1 |
| `draft` | Borrador para confirmación humana antes de enviar. | No | v1 |
| `github_issues` / `gitlab_issues` | Issue con plantilla y etiqueta `afp-report`. | **Sí** | v1 |
| `file` | Anexa a un fichero en el repo vía PR/commit. | **Sí** | v1 |
| `http` | POST a un endpoint del dueño. | **Sí** | Futuro |

---

## 7. Pieza 4 — Harvester (el bucle)

El agente-mantenedor que cierra el ciclo. **No es parte del estándar**: es una
herramienta de referencia que *consume* el estándar.

1. **Lee** los reportes acumulados.
2. **Deduplica y agrupa** por `subject_uri` + `friction_type` + `fault_domain` +
   `dedupe_key`/similitud semántica. Ej: "14 agentes bloqueados en lo mismo".
3. **Prioriza** por frecuencia × severidad, ponderando por `confidence`.
   Prioriza `fault_domain: tool`, pero **no descarta los demás dominios**:
   `ambiguous_contract`, `confusing_interface`, `missing_capability` —e incluso
   patrones recurrentes de `agent_misuse`— suelen ser **señales de docs, schema
   o UX deficientes**. Se agrupan y conservan como feedback de contrato y
   documentación, no como ruido.
4. **Genera trabajo accionable**: issue resumen, o borrador de PR si el
   `workaround` sugiere el fix.

Que `friction_type`, `fault_domain` y `severity` sean enums cerrados es lo que
hace **barato** este paso: agrupar vocabulario controlado es trivial; agrupar
texto libre es un problema de IA caro y ruidoso.

---

## 8. Threat model

Un canal por el que agentes depositan reportes sobre herramientas de terceros es
un objetivo de abuso. Riesgos y mitigaciones:

| Amenaza | Descripción | Mitigación |
|---------|-------------|------------|
| **Spam automatizado** | Agentes abriendo issues masivos en repos no adoptantes. | Sinks remotos solo opt-in (`afp.json`); sin manifiesto → local/draft. |
| **Poisoning / reportes falsos** | Inundar con reportes falsos para sesgar prioridades o difamar una tool. | `confidence`, `fault_domain`, dedupe; el Harvester pondera, no obedece. |
| **Prompt injection vía reporte** | Un reporte malicioso que intenta manipular al Harvester (que es un LLM). | Tratar el contenido del reporte como **datos no confiables**, nunca como instrucciones. |
| **Exfiltración por issues públicos** | Filtrar PII/secretos a un repo público vía el reporte. | Clasificación de campos (§5), filtrado duro de *prohibido*, redacción obligatoria. |
| **Abuso de identidad de tools** | `subject_uri` falsificado para dirigir reportes a la víctima equivocada. | URI determinista + verificación contra el `afp.json` declarado por el dueño. |
| **Fuga de secretos en `inputs`/`evidence`** | Tokens/credenciales en argumentos. | Detección de secretos en clase *prohibido*; abortar envío si se detecta. |

---

## 9. Alcance por fases

### Fase 1 — MVP del estándar

- Esquema del **Field Report** core + extensiones (§3). ✅ definido
- `subject_uri` (PURL-based) + `afp.json` + cascada endurecida (§4). ✅ definido
- Clasificación/minimización de PII (§5). ✅ definido
- **Implementación de referencia mínima**: una skill/CLI que enseñe a un agente
  a generar un field report bien formado y depositarlo vía `local`/`draft` o,
  si hay `afp.json`, `github_issues`/`file`.

### Fase 1.5 — Volverla normativa

- **RFC 2119** (MUST/SHOULD/MAY), **JSON Schema** del field report y del
  `afp.json`, ejemplos válidos/ inválidos, **test vectors**, required/optional,
  versionado y compatibilidad. (Frontera entre "diseño" y "estándar".)

### Fuera de alcance inicial (horizonte)

- **Harvester** completo (§7), sink `http`, extensión *in-band* de MCP,
  sumidero comunitario.

---

## 10. Decisiones de diseño y su porqué

| Decisión | Razón |
|----------|-------|
| El dato es el centro, no el transporte | Permite que MCP, CLI, skill, API y GUI compartan un mismo protocolo. |
| Enums cerrados (`friction_type`, `fault_domain`, `severity`) | Hace barata la deduplicación/agrupación del Harvester. |
| `fault_domain` separado de `friction_type` | No toda fricción se origina en la tool; genera confianza del mantenedor y preserva señales de docs/contrato. |
| Core required + extensiones optional | Reporte mínimo barato de generar = más adopción; el resto enriquece. |
| `subject_uri` apoyado en PURL | Reutilizar un estándar ECMA existente baja la fricción de adopción. |
| Redacción/minimización de PII | Principal riesgo legal; evita filtrar datos a repos de terceros. |
| Sin manifiesto → nunca auto-envío | Auto-abrir issues = spam y abuso; adopción remota siempre opt-in. |
| Bridge OTel (`trace_id`) en vez de "anti-telemetría" | AFP es complementario: feedback derivable de traces, no un sustituto. |
| Sumidero comunitario descartado | Rompe la descentralización; gobernanza/coste/spam/confianza. |
| Harvester fuera del estándar | Permite múltiples consumidores del mismo formato, como navegadores sobre HTTP. |

---

## 11. Glosario

- **AFP** — Agent Feedback Protocol (nombre de trabajo).
- **Field report** — la unidad básica: un "parte de campo" que un agente deja
  tras encontrar fricción con una herramienta.
- **`subject_uri`** — identificador URI único y determinista de una tool, basado
  en PURL/URIs nativas donde sea posible.
- **`friction_type`** — qué tipo de fricción ocurrió.
- **`fault_domain`** — dónde parece estar la causa de la fricción (tool /
  agente / entorno / contrato). Dominio probable, no juicio de culpa.
- **Sink** — el canal/destino por el que viaja un field report.
- **Harvester** — agente que consume los reportes y genera mejoras.
- **Harness** — el entorno agéntico (Claude Code, Cursor, Cline, Aider…).
- **PURL** — Package URL, norma ECMA-427 para identificar paquetes.
- **OTel** — OpenTelemetry; AFP enlaza con sus traces vía `trace_id`.
