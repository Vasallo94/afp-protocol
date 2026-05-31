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
verifica que el `subject_uri` del reporte coincide con el del manifiesto
(anti-spoofing).

## Tests

```bash
uv run pytest -v
```
