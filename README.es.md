# AFP — Agent Feedback Protocol (reference implementation)

> English: [README.md](README.md)

Implementación de referencia en Python del **camino de vuelta** que le falta a MCP:
un canal estándar para que un agente de IA reporte la *fricción* que encontró al
usar una herramienta, dirigido al mantenedor de esa herramienta.

**Spec normativa:** [spec/SPEC.md](spec/SPEC.md) (inglés, RFC 2119) · [JSON Schemas canónicos](spec/schemas/) · [test vectors de conformidad](spec/vectors/)
Documento de diseño (razonamiento): `docs/superpowers/specs/2026-05-30-afp-protocol-design.md`

## Instalación

```bash
uv sync
```

## Uso de la CLI

```bash
# 1. Construir un field report completo a partir de un JSON parcial
uv run afp report --from partial.json --out report.json

# 2. Validar (JSON Schema + hard-block de secretos)
uv run afp validate report.json

# Validar un manifiesto afp.json
uv run afp validate-manifest afp.json

# 3. Depositar respetando la política de routing
#    Sin afp.json en --dir, solo se permite local/draft (nunca auto-envío remoto).
uv run afp submit report.json --dir . --sink draft

# Alternativa atómica: construir y depositar en una sola llamada
uv run afp report --from partial.json --submit --dir . --sink draft

# Revisar drafts locales antes de promoverlos
uv run afp drafts list --dir .
uv run afp drafts show afp_<id> --dir .

# Promoción explícita tras revisión humana
uv run afp drafts promote afp_<id> --dir . --sink github_issues
```

### Señal de revisión (`AFP-REVIEW:`)

Cada vez que un envío se deposita como `draft` (`submit`, `report --submit`,
`dogfood` sin manifiesto), AFP emite en **stderr** una línea con el prefijo
estable `AFP-REVIEW:` indicando cuántos drafts hay pendientes y el comando para
revisarlos:

```
AFP-REVIEW: 2 drafts pendientes de revisión humana → afp drafts list --dir .
```

Es un **contrato documentado**: un harness agéntico puede detectar el prefijo
`AFP-REVIEW:` en stderr para mostrar al humano que hay drafts que aprobar, y un
humano lo lee directamente. El `OK: ... -> draft:/ruta` sigue en stdout.

`partial.json` mínimo:

```json
{
  "subject_uri": "pkg:pypi/ruff",
  "goal": "lintear el proyecto",
  "expectation": "salida JSON con los errores",
  "observed": "salida en texto plano sin estructura",
  "friction_type": "wrong_output",
  "fault_domain": "tool",
  "severity": "degraded"
}
```

## Integraciones de harness

[integrations/](integrations/) enseña a los agentes a emitir drafts AFP cuando
encuentran fricción con una herramienta, y a verificar/descartar drafts antiguos
(siempre `--sink draft`; una persona revisa y promueve).

Instala AFP una vez:

```bash
uv tool install git+https://github.com/Vasallo94/afp-protocol
```

Después instala la integración del harness:

```bash
afp integrations install codex --global
afp integrations install claude-code --global
afp integrations install cursor --project .
afp doctor
```

Las integraciones se copian desde recursos empaquetados; no hace falta clonar
este repo. Los agentes solo emiten drafts. La promoción a issues la decide un
humano con `afp drafts list/show` y `afp drafts promote`.

Los mantenedores de herramientas pueden inicializar el manifiesto de confianza
que habilita la promoción remota revisada:

```bash
afp init \
  --dir . \
  --subject mcp://github.com/acme/weather-mcp \
  --sink github_issues \
  --repo acme/weather-mcp
```

## Dogfooding de AFP sobre AFP

Para reportar fricción encontrada usando esta propia implementación:

```bash
uv run afp dogfood \
  --goal "validar un reporte generado por AFP" \
  --expectation "la CLI debería explicar por qué falla" \
  --observed "el mensaje no dejaba claro qué campo era inválido" \
  --friction-type confusing_interface \
  --fault-domain tool \
  --severity degraded \
  --sink draft
```

Por defecto, esto crea un borrador local en `.afp/drafts/`. El repo AFP declara
su propio `afp.json`, así que los reportes revisados manualmente pueden
promoverse después a issues de `Vasallo94/afp-protocol` usando el sink remoto.

## Regla de oro de seguridad

Sin un `afp.json` declarado por la tool, AFP **nunca** auto-envía a un repo de
terceros: solo escribe en `local` (spool) o `draft` (revisión humana). El envío
remoto (p.ej. `github_issues`) es siempre **opt-in del mantenedor**, y además se
verifica que el `subject_uri` del reporte **cae bajo** el que declara el
manifiesto (anti-spoofing):

- **PURL**: misma base de paquete (la `@version` y el `#fragment` no cambian el dueño).
- **http(s)/mcp**: mismo host/autoridad (`api.acme.com.evil.com` ≠ `api.acme.com`)
  y el path del reporte es el del manifiesto o un sub-path por segmentos
  (`/v1` posee `/v1/charges`, no `/v1abc`).

Tratamiento de datos sensibles (§5): los **secretos de alta confianza** (tokens,
claves, JWT, Bearer) son un **hard-block** — si se detectan, el envío se aborta.
La **PII directa** (email) **no aborta**: se **redacta** a `[REDACTED_EMAIL]` y el
reporte continúa, porque un email mencionado en texto libre suele ser información
útil para el mantenedor.

## Semántica de entrega (at-least-once, idempotente en remotos)

Los **sinks remotos** (`github_issues`/`gitlab_issues`) son **idempotentes por
`report_id`**: un ledger local (`.afp/submitted.json`) mapea `report_id -> ref`,
así que reenviar el mismo reporte (p.ej. un reintento tras un timeout de red cuyo
envío sí llegó) devuelve la ref previa en vez de abrir un issue duplicado. Es
determinista y no depende del lag de indexado de búsqueda del proveedor.

Los **sinks locales** no se deduplican: `local` es un spool de append y `draft`
ya se sobreescribe por `report_id`. La deduplicación *semántica* entre reportes
distintos (agrupar "14 agentes bloqueados en lo mismo") sigue siendo del
**Harvester** (§7 del spec).

## Sink GitLab (self-hosted / on-premise)

Para enrutar reportes a un GitLab interno, la tool declara en su `afp.json`:

```json
{
  "afp_version": "0.2",
  "subject_uri": "mcp://<gitlab-host>/<grupo>/<proyecto>",
  "sink": {
    "type": "gitlab_issues",
    "host": "<gitlab-host>",
    "repo": "<grupo>/<proyecto>",
    "label": "afp-report"
  },
  "redaction": "required",
  "accepts_remote": true
}
```

Requiere `glab` instalado y autenticado contra el host
(`glab auth login --hostname <host>`). La promoción a issue es explícita y
revisada: `afp drafts promote <id> --dir <repo> --sink gitlab_issues`.

## Tests

```bash
uv run pytest -v
```
