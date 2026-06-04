# Evaluación de arquitectura — AFP (reference impl, Fase 1a)

**Estado:** Completada · **Fecha:** 2026-06-04 · **Revisor:** Claude (Opus 4.8) vía `/engineering:architecture`
**Alcance:** `src/afp/` (dato, identidad, transporte, routing) contra el spec
[`docs/superpowers/specs/2026-05-30-afp-protocol-design.md`](../superpowers/specs/2026-05-30-afp-protocol-design.md)

> **Para agentes futuros:** este documento es la foto de la arquitectura en 2026-06-04 y el
> porqué de los issues abiertos (#5–#11). Si trabajas en alguno de esos issues, lee aquí el
> razonamiento completo antes de tocar el código. Si el código ha cambiado, valida primero que
> el hallazgo sigue vigente — las referencias `archivo:línea` reflejan el estado de esa fecha.

---

## Resumen ejecutivo

La implementación es **fiel al spec y arquitectónicamente sólida** para un MVP. Las 4 piezas del
diseño (dato / identidad / transporte / bucle) están limpiamente separadas, el Harvester está
correctamente *fuera* del código (es un consumidor, no parte del estándar), y los defaults de
seguridad —no auto-envío sin manifiesto, opt-in remoto, hard-block de secretos antes de validar
schema— están bien implementados y son la mayor fortaleza del diseño.

Los problemas no son de corrección funcional sino **estructurales de cara a la evolución**:
rigidez forward-compat que choca con la naturaleza de "protocolo", duplicación que se va a
triplicar con cada sink nuevo, y un hueco de seguridad concreto (inyección de markdown /
notificaciones en el cuerpo del issue) que el propio threat model anticipa pero el renderer no
cubre.

Ningún hallazgo bloquea Fase 1a. #1 (extensibilidad) y #2 (saneo del issue) son los que tienen
consecuencias de protocolo/seguridad y merecen decisión explícita.

## Mapa de capas (estado 2026-06-04)

```
CLI (cli.py) ── orquesta: build → validate → discover → route → submit
  │
  ├─ models.FieldReport ........ el DATO (dataclass + enums cerrados)
  ├─ validate.validate_report .. hard-block secretos → JSON Schema → subject_uri
  ├─ identity.validate_subject_uri ... PURL + esquemas nativos
  ├─ discovery.discover ........ POLÍTICA: qué sinks se permiten (RoutingDecision)
  ├─ sinks.route ............... ENFORCEMENT: anti-spoofing + elige sink
  └─ sinks.get_sink ............ FACTORY: construye el sink concreto
```

La tripartición **discover (decide) → route (enforce) → get_sink (construye)** es el mayor acierto
estructural: la política de seguridad vive separada de la construcción, y `route` añade defensa en
profundidad (anti-spoofing) sobre lo que `discover` ya filtró.

## Fortalezas confirmadas

- **Separación de las 4 piezas** del spec; Harvester fuera del código (correcto: es un consumidor).
- **Seguridad por defecto:** sin manifiesto → solo `local`/`draft` (`discovery.py:33-35`);
  remoto solo con `accepts_remote=True`; anti-spoofing en `route` (`sinks/__init__.py:60-84`);
  hard-block de secretos *antes* de validar schema (`validate.py:40-42`).
- **Flujo draft con revisión humana** (`drafts list/show/promote`) — alineado con el threat model
  de spam.
- **Reutiliza estándares** en vez de reinventar: PURL (`identity.py`), JSON Schema para report y
  manifiesto, enums cerrados (dedup barato, coherente con §10 del spec).
- **Shell-out sin `shell=True`** (forma argv) en GitHub/GitLab → sin inyección de shell.

## Hallazgos priorizados

| # | Severidad | Hallazgo | Dónde | Issue |
|---|-----------|----------|-------|-------|
| 1 | **Alta** | Rigidez forward-compat: el report rechaza campos desconocidos en *dos* capas | `models.py:75`, `field_report.schema.json:6` | [#7](https://github.com/Vasallo94/afp-protocol/issues/7) |
| 2 | **Alta** | Inyección de markdown / notificaciones en el cuerpo del issue | `sinks/github.py:22-72`, `gitlab.py:24-72` | [#5](https://github.com/Vasallo94/afp-protocol/issues/5) |
| 3 | Media | Renderer de issue triplicado + GitHub/GitLab ~95% copia-pega | `github.py`, `gitlab.py`, `cli.py:68` | [#6](https://github.com/Vasallo94/afp-protocol/issues/6) |
| 4 | Media | Sin idempotencia: reenviar = issue duplicado / línea duplicada | `sinks/github.py:74`, `local.py:13` | [#9](https://github.com/Vasallo94/afp-protocol/issues/9) |
| 5 | Media | `_owned_base` es PURL-céntrico; frágil para subjects `https`/`mcp` | `sinks/__init__.py:17-34` | [#8](https://github.com/Vasallo94/afp-protocol/issues/8) |
| 6 | Baja | Hard-block de email aborta reportes legítimos que *mencionan* un email | `redact.py:21` | [#10](https://github.com/Vasallo94/afp-protocol/issues/10) |
| 7 | Baja | `date-time` demasiado permisivo (acepta fecha sin hora) | `validate.py:26-31` | [#11](https://github.com/Vasallo94/afp-protocol/issues/11) |
| 8 | Baja | Versionado sin negociación de compatibilidad (acoplado a #1) | `models.py`, `manifest.py` | [#7](https://github.com/Vasallo94/afp-protocol/issues/7) |

---

### 1 — Rigidez forward-compat (Alta) · *la decisión estructural más importante*

`FieldReport.from_dict` hace `cls(**data)` (`models.py:75`): un campo opcional que no exista en la
dataclass lanza `TypeError`. Y el schema del report tiene `additionalProperties: false`
(`field_report.schema.json:6`). Resultado: un reporte `afp/0.3` con una extensión nueva **falla en
ambas capas** contra esta librería `afp/0.2`.

**Por qué importa:** AFP se vende como *protocolo* ("mil navegadores hablan HTTP"). HTTP, MCP y OTel
toleran campos desconocidos por diseño — es lo que permite que productor y consumidor evolucionen a
ritmos distintos. Hoy `schema_version` existe pero no se usa para relajar nada. Un Harvester escrito
contra esta lib rechazaría reportes de agentes más nuevos, justo el escenario que el protocolo debe
soportar.

**Recomendación:** definir la política de extensibilidad *ahora* (es Fase 1.5, pero condiciona
todo): (a) `additionalProperties: true` en *extensiones* + preservar `**extra` en la dataclass, o
(b) regla explícita "unknown fields → warn & drop, nunca abort", o (c) estricto + bump de versión
obligatorio. Decisión de protocolo → merece un ADR propio (issue [#7](https://github.com/Vasallo94/afp-protocol/issues/7)).

### 2 — Inyección de markdown / notificaciones en el issue (Alta) · *hueco del threat model*

El shell-out usa forma argv sin `shell=True` (`github.py:74`) → **no hay inyección de shell**. Pero
el contenido controlado por el agente (`observed`, `goal`, `workaround`) se interpola crudo en el
cuerpo markdown (`github.py:22-72`):

- Un ` ``` ` o `</details>` en `observed` rompe el bloque "Raw AFP JSON" y reestructura el issue.
- `@org/team` o `#123` en texto libre generan **menciones y back-references reales** en
  GitHub/GitLab — notificaciones a terceros y cross-links, *antes* de que ningún Harvester (el LLM
  que el §8 sí protege) toque el dato.

El §8 cubre "prompt injection vía reporte" para el Harvester, pero el **efecto de notificación
ocurre en el sink**, aguas arriba del Harvester. Es exactamente el vector de spam/abuso que el
diseño quiere evitar.

**Recomendación:** sanear los campos libres en el renderer: neutralizar autolinks (`@`→`@​`,
`#`→`#​` o envolver en backticks), y cercar el JSON con una valla de backticks más larga que
cualquier run presente en el contenido. Barato y cierra el agujero. Implementar en el renderer
compartido del hallazgo #3.

### 3 — Renderer triplicado (Media)

`_title`/`_body` en `github.py` y `gitlab.py` son idénticos salvo el comando; `_render_report_markdown`
en `cli.py:68` es un tercer renderer casi gemelo. Con `file`/`http` (Fase 1b) serán más. Cualquier
cambio de plantilla (incluido el saneo del #2) hay que hacerlo en N sitios.

**Recomendación:** extraer `render_issue(report) -> (title, body)` compartido (`sinks/render.py` o
método en una `IssueSink(Sink)` base). Centraliza la plantilla y el punto de saneo del #2.

### 4 — Sin idempotencia (Media)

`submit` abre un issue nuevo en cada ejecución; `local` (`local.py:13`) anexa otra línea. El
`report_id` viaja en el cuerpo pero nadie lo consulta para detectar duplicados. Un reintento por
timeout de red tras un envío que sí llegó → issue duplicado.

El spec pone el dedupe en el Harvester (defendible para *agrupar*), pero no cubre el **doble-submit
accidental** del mismo `report_id`.

**Recomendación:** documentar la semántica "at-least-once, no idempotente"; idealmente buscar por
`report_id` antes de crear en `github_issues`/`gitlab_issues`.

### 5 — `_owned_base` frágil para no-PURL (Media)

`_owned_base` (`sinks/__init__.py:17`) normaliza bien PURL (quita `@version`) y MCP (quita
`#fragment` → `mcp://github.com/user/repo` ✓). Pero para `https://api.stripe.com/v1/charges` la
"base" es casi la URL completa: un manifiesto que declara `.../charges` **bloquearía** un reporte
sobre `.../refunds` del mismo dueño, y un `?query=`/trailing slash rompe la igualdad. El
anti-spoofing es la mitigación estrella del §8; para subjects web es a la vez demasiado estricto y
sin normalizar.

**Recomendación:** para `http(s)`/`mcp`, comparar por **autoridad/host** (o host+prefijo declarado),
no por path completo. Coherente con §10b (validación de URLs laxa por diseño en Fase 1a).

### 6 y 7 — Footguns menores

- **#6:** el regex de email (`redact.py:21`) es un *hard-block que aborta el envío*. Un
  `observed: "el error mostraba soporte@empresa.com"` —contenido legítimo— se rechaza entero.
  Considerar **redactar-y-continuar** para email (abortar tiene sentido para tokens, no tanto para
  un email mencionado).
- **#7:** `datetime.fromisoformat` (`validate.py:27`) en 3.11+ acepta `Z` (bien, cubierto por
  `requires-python>=3.11`), pero también acepta `"2026-05-30"` (fecha sin hora) como `date-time`
  válido. Si el `timestamp` se usa para ordenar/agrupar, endurecer a RFC 3339 estricto.

### 8 — Versionado sin negociación (Baja, pero estructural)

`afp_version`/`schema_version` son strings libres sin chequeo de compatibilidad mayor/menor.
Diferido a Fase 1.5 en el spec, pero está acoplado al #1: la política de versiones y la de
campos-desconocidos son **la misma decisión** y deberían resolverse juntas (issue [#7](https://github.com/Vasallo94/afp-protocol/issues/7)).

## Acoplamientos y deuda (vista de conjunto)

- **Bueno:** `Sink` como interfaz mínima (`base.py`) desacopla transporte de política.
  `discover`/`route`/`get_sink` separan decisión/enforcement/construcción. Validación apoyada en
  PURL y JSON Schema.
- **A vigilar:** el renderizado de issues (#3) y la normalización de identidad (#5) son los dos
  puntos que **escalan mal** al añadir sinks/esquemas de subject. Resolverlos antes de Fase 1b
  evita pagar el refactor 5 veces.

## Plan de ataque recomendado

1. **Saneo del cuerpo del issue (#2 → [#5](https://github.com/Vasallo94/afp-protocol/issues/5))** — seguridad, barato, alineado con §8. *Hacer ya.*
2. **Extraer renderer compartido (#3 → [#6](https://github.com/Vasallo94/afp-protocol/issues/6))** — habilita el saneo del #2 en un solo punto y prepara Fase 1b.
3. **ADR extensibilidad + versionado (#1 + #8 → [#7](https://github.com/Vasallo94/afp-protocol/issues/7))** — condiciona la interoperabilidad real. *Antes de declarar la spec normativa (Fase 1.5).*
4. **Normalizar `_owned_base` por host (#5 → [#8](https://github.com/Vasallo94/afp-protocol/issues/8))** y documentar semántica at-least-once (#4 → [#9](https://github.com/Vasallo94/afp-protocol/issues/9)).
5. **abort-vs-redact email (#6 → [#10](https://github.com/Vasallo94/afp-protocol/issues/10))** y endurecer `date-time` (#7 → [#11](https://github.com/Vasallo94/afp-protocol/issues/11)).

> Disciplina de ejecución (harnesses): cada issue lleva criterios de aceptación con **tests**.
> Aplicar TDD donde toque comportamiento (saneo, routing, redacción, validación): escribir el test
> que falla primero, luego la implementación mínima. No mergear hallazgos de seguridad (#2, #5) sin
> vectores de prueba que cubran el caso adversario.
