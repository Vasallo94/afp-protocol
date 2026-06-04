# AFP — Agent Feedback Protocol (reference implementation)

Implementación de referencia en Python del **camino de vuelta** que le falta a MCP:
un canal estándar para que un agente de IA reporte la *fricción* que encontró al
usar una herramienta, dirigido al mantenedor de esa herramienta.

Spec: `docs/superpowers/specs/2026-05-30-afp-protocol-design.md`

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

## Semántica de entrega (at-least-once, no idempotente)

`submit` deposita el reporte una vez por invocación y **no deduplica**: reenviar
el mismo reporte abre otro issue (`github_issues`/`gitlab_issues`) o añade otra
línea al spool (`local`). El `report_id` viaja en el cuerpo, pero hoy no se
consulta para evitar duplicados. La deduplicación y el agrupamiento son
responsabilidad del **Harvester** (§7 del spec), por diseño. Si reintentas tras
un timeout de red cuyo envío sí llegó, revisa antes el destino. (Dedupe en el
propio sink: backlog [#9](https://github.com/Vasallo94/afp-protocol/issues/9).)

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
