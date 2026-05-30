# AFP — Agent Feedback Protocol

**Documento de diseño** · v0.1 · 2026-05-30

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
- **No es telemetría de errores.** Sentry y los logs reportan el *síntoma
  técnico* (excepción en la línea 42). AFP reporta la *intención frustrada*:
  qué quería lograr el agente, qué esperaba de la tool, y por qué su plan se
  rompió.

### Principio rector

> El centro del protocolo no es el transporte, es **el dato**. Si el field
> report y la identidad de la tool están bien definidos, el transporte y el
> consumidor del dato son intercambiables. Diseñamos para el bucle completo,
> pero el corazón es agnóstico.

---

## 2. Arquitectura general

AFP se compone de **cuatro piezas separadas y apilables**. Cada una se entiende,
se construye y se prueba de forma independiente.

```
┌─────────────────────────────────────────────────────────────┐
│  1. EL DATO — "Field Report"                                  │
│     Esquema universal y agnóstico al transporte.              │
│     Captura: intención, plan, expectativa, qué pasó, contexto │
│     Es el corazón. Todo lo demás sirve a esto.                │
├─────────────────────────────────────────────────────────────┤
│  2. LA IDENTIDAD — "Tool Anchor"                              │
│     Cómo se nombra una herramienta de forma única y           │
│     cómo el agente descubre DÓNDE mandar el reporte.          │
│     Funciona para MCP, CLI, skill, API, GUI, lo que sea.      │
│     Capa 1: manifiesto declarado por la tool (preferente)     │
│     Capa 2: inferencia (repo del binario, package.json…)      │
├─────────────────────────────────────────────────────────────┤
│  3. EL TRANSPORTE — "Sinks"                                   │
│     Por dónde viaja el reporte hasta su casa.                 │
│     Intercambiable: issue de GitHub, fichero en repo,         │
│     endpoint HTTP, carpeta local. El dato es el mismo.        │
├─────────────────────────────────────────────────────────────┤
│  4. EL BUCLE — "Harvester"                                    │
│     Agente-mantenedor que lee los reportes, deduplica,        │
│     prioriza y abre issues/PRs de mejora. Cierra el círculo.  │
│     NO es parte del estándar: es UN consumidor del estándar.  │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de punta a punta

1. Un agente (en cualquier harness) usa una herramienta y su **plan se rompe**:
   la tool no se comportó como esperaba.
2. El agente genera un **Field Report** (pieza 1): qué quería, qué esperaba, qué
   recibió, en qué punto del plan se rompió.
3. Resuelve la **identidad** de la tool (pieza 2): "esta tool vive aquí, su
   buzón es este".
4. Deposita el reporte por el **transporte** que ese buzón indique (pieza 3).
5. Más tarde, el **Harvester** del dueño (pieza 4) recoge todos los reportes,
   agrupa los repetidos, prioriza y genera trabajo de mejora real.

### Frontera del estándar

El **estándar** son las piezas **1, 2 y el formato del transporte (3)**. El
**Harvester (4) NO es el estándar** — es *un* consumidor de él. Pueden existir
muchos Harvesters distintos (uno simple en bash, uno sofisticado con IA, el
tuyo, el de otra empresa) y todos funcionan porque hablan el mismo formato.
Igual que existen mil navegadores distintos que hablan HTTP.

---

## 3. Pieza 1 — El Field Report (el dato)

Regla de oro: **captura la intención frustrada, no el error técnico.**

### 3.1 Esquema

**Bloque A — Identidad (a quién va dirigido)**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `tool_anchor` | string (URI) | Identificador único de la herramienta (ver §4). |
| `tool_version` | string | Versión observada de la tool. Sin esto, el mantenedor no sabe si ya lo arregló. |

**Bloque B — La intención (lo que ningún sistema captura hoy)**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `goal` | string | Qué intentaba lograr el agente, en lenguaje de producto. |
| `plan_step` | string | En qué punto de su plan estaba. Ej: "Paso 3 de 5: tras resolver el objetivo, calcular el FOV". |
| `expectation` | string | Qué esperaba que devolviera/hiciera la tool. |

**Bloque C — Lo que pasó (la fricción)**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `observed` | string | Qué recibió/ocurrió en realidad. |
| `friction_type` | enum | Categoría acotada (clave para deduplicar). Ver §3.2. |
| `severity` | enum | `blocked` \| `degraded` \| `cosmetic`. Ver §3.3. |
| `workaround` | string \| null | Si encontró una salida, cuál. (Sugiere el fix al mantenedor.) |

**Bloque D — Contexto reproducible**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `inputs_redacted` | object | Argumentos usados, **con PII eliminada** (ver §3.4). |
| `harness` | string | Desde dónde se generó (`claude-code`, `cursor`, `cline`, `aider`…). |
| `timestamp` | string (ISO 8601) | Cuándo ocurrió. |
| `report_id` | string | Identificador único del reporte. |
| `schema_version` | string | Versión del esquema AFP, ej. `afp/0.1`. |

### 3.2 Valores de `friction_type` (enum cerrado)

- `bug` — la tool falla de forma demostrable.
- `undocumented_behavior` — funciona, pero de forma no documentada/sorprendente.
- `missing_capability` — falta una capacidad que el plan necesitaba.
- `confusing_interface` — la interfaz/contrato indujo a error.
- `wrong_output` — devolvió algo incorrecto o en formato inesperado.
- `integration_mismatch` — falla al integrarse con el resto del sistema/otras tools.

### 3.3 Valores de `severity` (enum cerrado)

- `blocked` — el agente no pudo continuar su plan.
- `degraded` — continuó, pero con esfuerzo o riesgo extra.
- `cosmetic` — molestia menor, sin impacto en el resultado.

### 3.4 Redacción de PII (regla dura)

La redacción de PII **no es opcional**. Un agente reportando "fallé al procesar
este email" podría filtrar el dato de un usuario al repositorio público de un
tercero. El campo `inputs_redacted` **debe** estar redactado antes de enviarse.
El manifiesto de la tool (`afp.json`) puede marcar `"redaction": "required"`
para reforzarlo. Este es el principal riesgo legal del proyecto y una decisión
de diseño, no un detalle de implementación.

### 3.5 Universalidad del esquema (prueba de fuego)

El mismo esquema, **sin añadir ni quitar campos**, sirve para cualquier tipo de
herramienta. Lo único que cambia es el prefijo del `tool_anchor`:

```json
// CLI
{ "tool_anchor": "afp://cli/npm/eslint", "tool_version": "9.2.0",
  "goal": "Auto-arreglar problemas de lint antes de commitear",
  "plan_step": "3/6 — limpiar el código antes de pasar los tests",
  "expectation": "--fix corregiría las comillas y saldría con código 0",
  "observed": "Salió con código 1 sin explicar qué regla no era auto-fixable",
  "friction_type": "confusing_interface", "severity": "degraded",
  "workaround": "Parseé el stdout a mano para encontrar la regla",
  "inputs_redacted": { "args": ["--fix", "src/"] }, "harness": "claude-code" }

// Skill
{ "tool_anchor": "afp://skill/superpowers/test-driven-development",
  "tool_version": "5.1.0",
  "goal": "Aplicar TDD a un bugfix en una base sin tests previos",
  "plan_step": "1/4 — escribir el test que falla primero",
  "expectation": "Cubriría el caso de codebase sin framework de test",
  "observed": "Asume que ya existe un test runner; no dice qué hacer si no hay",
  "friction_type": "missing_capability", "severity": "blocked",
  "workaround": "Configuré pytest por mi cuenta antes de seguir la skill",
  "inputs_redacted": {}, "harness": "claude-code" }

// GUI / plugin de clic
{ "tool_anchor": "afp://app/figma/brand-exporter", "tool_version": "2.1.0",
  "goal": "Exportar los assets de marca a PNG @2x",
  "plan_step": "4/4 — exportar tras seleccionar el frame",
  "expectation": "El botón 'Export' abriría el diálogo de exportación",
  "observed": "El botón no responde si no hay un frame seleccionado, sin avisar",
  "friction_type": "confusing_interface", "severity": "blocked",
  "workaround": "Seleccioné un frame a ciegas y reintenté",
  "inputs_redacted": { "action": "click", "target": "Export button" },
  "harness": "cursor" }

// API REST
{ "tool_anchor": "afp://api/api.stripe.com/v1/charges",
  "tool_version": "2024-06-20",
  "goal": "Crear un cargo de prueba en modo sandbox",
  "plan_step": "2/3 — cobrar tras validar el método de pago",
  "expectation": "Un error claro si falta el campo 'currency'",
  "observed": "Devolvió 400 con un mensaje genérico que no nombra el campo",
  "friction_type": "wrong_output", "severity": "degraded",
  "workaround": "Probé añadiendo campos uno a uno hasta acertar",
  "inputs_redacted": { "amount": "[REDACTED]" }, "harness": "aider" }
```

---

## 4. Pieza 2 — El Tool Anchor (identidad y descubrimiento)

Dos problemas distintos que deben resolverse por separado.

### 4.1 Nombrar la tool de forma única (`tool_anchor`)

Esquema de nombres tipo URI, con un prefijo que indica el ecosistema:

```
afp://<tipo>/<localizador>[#<sub-herramienta>]
```

| Tipo | Ejemplo | Localizador |
|------|---------|-------------|
| `mcp` | `afp://mcp/github.com/user/repo#nombre_tool` | repo + nombre de la tool MCP |
| `cli` | `afp://cli/npm/eslint` · `afp://cli/pypi/ruff` | registro + nombre del paquete |
| `skill` | `afp://skill/namespace/nombre-skill` | namespace + nombre de skill |
| `api` | `afp://api/host/ruta` | host + ruta |
| `app` | `afp://app/plataforma/plugin` | plataforma + plugin |
| `bin` | `afp://bin/sha256:<hash>` | hash del binario (último recurso) |

**Requisito clave: el `tool_anchor` es determinista.** Dos agentes distintos, en
harness distintos, usando la misma tool, generan **el mismo anchor**. Sin esto,
el Harvester no puede agrupar nada.

### 4.2 Descubrir el buzón (cascada de 2 capas)

El agente prueba de arriba a abajo:

```
Capa 1 (preferente): MANIFIESTO DECLARADO — "afp.json"
  La tool publica un fichero estándar que declara su buzón y esquema.
  → MCP:    en su capability/metadata.
  → CLI:    campo en package.json / pyproject.toml.
  → Repo:   /.well-known/afp.json o /afp.json en la raíz.
  → Skill:  campo en el frontmatter de la skill.

Capa 2 (fallback): INFERENCIA — valor desde el día uno
  Si no hay manifiesto, el agente deduce la casa de lo que ve:
  - campo "bugs"/"repository" de package.json
  - git remote del binario
  - host de la API
  → Deposita en el canal genérico de ese sitio (p.ej. GitHub issues).
```

La **Capa 2 (inferencia)** es lo que rompe el problema del huevo y la gallina:
AFP aporta valor incluso para tools que no saben que existe. La adopción
explícita (Capa 1) llega después, atraída por ese valor.

> **Descartado del núcleo (YAGNI):** un "sumidero comunitario" central (registro
> neutral que recibe reportes anónimos sobre cualquier tool) se consideró y se
> descartó del alcance v1. Rompe el carácter descentralizado del resto del
> diseño e introduce problemas de gobernanza, coste de operación, spam,
> envenenamiento y confianza que ninguna otra pieza tiene. Queda como posible
> extensión futura opcional, de la que el protocolo **no depende**.

### 4.3 Formato del manifiesto `afp.json`

```json
{
  "afp_version": "0.1",
  "tool_anchor": "afp://mcp/github.com/user/nadir-astro",
  "sink": { "type": "github_issues", "repo": "user/nadir-astro", "label": "afp-report" },
  "redaction": "required",
  "schema_extensions": []
}
```

---

## 5. Pieza 3 — Transporte (Sinks)

No se inventa canal nuevo; se reutilizan los existentes. El `afp.json` declara
cuál usa la tool. El **dato es idéntico**; solo cambia el sobre.

| Tipo de sink | Comportamiento | Estado |
|--------------|----------------|--------|
| `github_issues` / `gitlab_issues` | Abre un issue con plantilla y etiqueta `afp-report`. | v1 |
| `file` | Anexa el reporte a un fichero en el repo (p.ej. `.afp/reports.jsonl`) vía PR/commit. | v1 |
| `local` | Carpeta local, para tools en desarrollo. | v1 |
| `http` | POST a un endpoint que el dueño exponga. | Futuro |

---

## 6. Pieza 4 — Harvester (el bucle)

El agente-mantenedor que cierra el ciclo. **No es parte del estándar**: es una
herramienta de referencia que *consume* el estándar. Su trabajo:

1. **Lee** los reportes acumulados (issues / fichero / endpoint).
2. **Deduplica y agrupa** por `tool_anchor` + `friction_type` + similitud
   semántica. Ej: "14 agentes bloqueados en lo mismo".
3. **Prioriza** por frecuencia × severidad.
4. **Genera trabajo accionable**: un issue resumen, o directamente un borrador
   de PR si el `workaround` sugiere el fix.

Que `friction_type` y `severity` sean enums cerrados es lo que hace **barato**
este paso: agrupar vocabulario controlado es trivial; agrupar texto libre es un
problema de IA caro y ruidoso.

---

## 7. Alcance de la Fase 1 (MVP del estándar)

**Dentro de Fase 1:**

- El esquema del **Field Report** (§3). ✅ definido
- El esquema de **`tool_anchor`** + el fichero **`afp.json`** + la cascada de
  descubrimiento de 2 capas (§4). ✅ definido
- Una **implementación de referencia mínima**: una skill/librería que enseñe a
  un agente a *generar* un field report bien formado y depositarlo vía `file` o
  `github_issues`.

**Fuera de Fase 1 (documentado como horizonte):**

- El **Harvester** completo (§6).
- El sink `http` (§5).
- La extensión *in-band* de MCP (adjuntar el reporte como metadato en la propia
  respuesta MCP).
- El **sumidero comunitario** (§4.2).

---

## 8. Decisiones de diseño y su porqué

| Decisión | Razón |
|----------|-------|
| El dato es el centro, no el transporte | Permite que MCP, CLI, skill, API y GUI compartan un mismo protocolo. |
| `friction_type` y `severity` como enums cerrados | Hace barata la deduplicación/agrupación del Harvester. |
| Redacción de PII obligatoria | Principal riesgo legal; evita filtrar datos de usuario a repos de terceros. |
| `tool_anchor` determinista | Sin identidad estable, no hay forma de agrupar reportes de agentes distintos. |
| Cascada manifiesto → inferencia | La inferencia da valor desde el día uno y rompe el bloqueo de adopción. |
| Sumidero comunitario descartado | Rompe la descentralización; introduce gobernanza, coste, spam y confianza. |
| Harvester fuera del estándar | Permite múltiples consumidores del mismo formato, como navegadores sobre HTTP. |

---

## 9. Glosario

- **AFP** — Agent Feedback Protocol (nombre de trabajo).
- **Field report** — la unidad básica de información: un "parte de campo" que un
  agente deja tras encontrar fricción con una herramienta.
- **Tool anchor** — identificador URI único y determinista de una herramienta.
- **Sink** — el canal/destino por el que viaja un field report a su casa.
- **Harvester** — agente que consume los reportes acumulados y genera mejoras.
- **Harness** — el entorno agéntico desde el que opera el LLM (Claude Code,
  Cursor, Cline, Aider…).
