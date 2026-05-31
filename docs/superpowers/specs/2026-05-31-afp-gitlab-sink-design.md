# AFP — Sub-proyecto 1: sink GitLab + manifiesto del MCP de Confluence

**Documento de diseño** · 2026-05-31

> Contexto: primer despliegue real de AFP fuera de los repos personales. Un MCP
> de Confluence (wiki del trabajo) se desplegará on-premise; los Claude Code del
> equipo deben poder reportar fricción a un issue del **GitLab interno** de la
> empresa. Caso de uso completo en la nota de Obsidian "Caso de uso trabajo -
> Confluence MCP on-premise". Spec base del protocolo:
> `2026-05-30-afp-protocol-design.md` (v0.2.1).

---

## 1. Objetivo

Añadir a AFP un sink `gitlab_issues` que abra issues en un **GitLab
self-hosted/on-premise** (host interno, no gitlab.com), y dejar listo el
`afp.json` que el repo del MCP de Confluence declarará para enrutar el feedback
a su proyecto en ese GitLab.

Esto desbloquea el primer test de utilidad real de AFP: varios Claude Code del
equipo capturando fricción del MCP de Confluence durante uso real, y esa
fricción aterrizando como issues accionables en GitLab (modernizando: hoy los
issues se gestionan en Kanbanize; AFP los lleva directos a donde vive el código).

## 2. No-objetivos (fuera de este sub-proyecto)

- El **resolver de herramientas instaladas** (binario → PURL → repo → afp.json).
  Es el Sub-proyecto 2; no hace falta para el MCP de Confluence porque es subject
  propio y trae su `afp.json`.
- Sink por **API REST** de GitLab. YAGNI: `glab` CLI encaja con el flujo actual
  (auth de `glab` ya hecho en terminal). Se añadirá un fallback API solo si
  `glab` no resulta viable en el entorno del trabajo.
- Sinks `file` / `http`.

## 3. Arquitectura: espejo del sink de GitHub

El núcleo de AFP (modelo, validación, redacción, discovery, routing,
anti-spoofing) ya existe y no cambia. Solo se añade **un sink** y se amplía el
schema del manifiesto. El anti-spoofing (comparación por base, sin `#fragment`
ni `@version`) ya cubre `gitlab_issues` porque está en `REMOTE_SINKS`.

### 3.1 `GitLabIssuesSink`

Fichero nuevo: `src/afp/sinks/gitlab.py`. Espejo de `GitHubIssuesSink`:

- Constructor: `GitLabIssuesSink(repo: str, label: str = "afp-report", host: str | None = None)`.
  - `repo`: ruta `grupo/proyecto` (o `grupo/subgrupo/proyecto`) en GitLab.
  - `host`: host interno (p.ej. `gitlab.empresa.local`). Si se da, se pasa a
    `glab` vía la variable de entorno `GITLAB_HOST`.
- `name = "gitlab_issues"`.
- `_title(report)` y `_body(report)`: idénticos en formato al sink de GitHub
  (título `[AFP/<severity>] <goal>`, cuerpo Markdown legible + bloque JSON crudo
  plegable en `<details>`). GitLab renderiza Markdown y `<details>` igual que
  GitHub.
- `submit(report)`:
  - Construye `cmd = ["glab", "issue", "create", "--repo", repo, "--title",
    title, "--description", body, "--label", label, "--yes"]`.
    (GitLab/`glab` usa `--description`, no `--body`; `--yes` evita prompts
    interactivos. Flags exactos a confirmar contra la versión de `glab` del
    trabajo — ver §6.)
  - Si `host` está definido: ejecutar con `env` que incluya `GITLAB_HOST=<host>`.
  - `subprocess.run(..., capture_output=True, text=True, timeout=30)`.
  - `TimeoutExpired` → `RuntimeError("glab issue create excedió el timeout")`.
  - `returncode != 0` → `RuntimeError(f"glab issue create falló: {stderr}")`.
  - Devuelve la URL del issue (`stdout.strip()`).

### 3.2 Schema del manifiesto (`afp_manifest.schema.json`)

Tres cambios mínimos:

1. Añadir `"gitlab_issues"` al enum de `sink.type`. Queda:
   `["github_issues", "gitlab_issues", "local", "draft"]`.
2. Añadir la propiedad opcional `"host": { "type": "string" }` dentro de `sink`.
3. Añadir un condicional `allOf` (espejo del de github): si
   `sink.type == "gitlab_issues"` entonces `sink` requiere `repo`.

### 3.3 Factoría `get_sink`

Añadir una rama en `src/afp/sinks/__init__.py`:

```python
    if sink_type == "gitlab_issues":
        if manifest is None:
            raise ValueError("gitlab_issues requiere un manifest con repo")
        return GitLabIssuesSink(
            repo=manifest.sink["repo"],
            label=manifest.sink.get("label", "afp-report"),
            host=manifest.sink.get("host"),
        )
```

`REMOTE_SINKS` ya incluye `gitlab_issues`, así que `route()` aplica el
anti-spoofing sin cambios.

## 4. Manifiesto del MCP de Confluence (`afp.json`)

Plantilla que se coloca en la raíz del repo del MCP de Confluence (en el GitLab
interno). Valores entre `<...>` se rellenan en el despliegue:

```json
{
  "afp_version": "0.2",
  "subject_uri": "mcp://<gitlab-host-interno>/<grupo>/<confluence-mcp>",
  "sink": {
    "type": "gitlab_issues",
    "host": "<gitlab-host-interno>",
    "repo": "<grupo>/<confluence-mcp>",
    "label": "afp-report"
  },
  "redaction": "required",
  "accepts_remote": true
}
```

El agente reportará sobre `mcp://<host>/<grupo>/<confluence-mcp>#<tool_que_falló>`
y el anti-spoofing por base dejará pasar el reporte al buzón correcto.

## 5. Política de privacidad y promoción (entorno corporativo)

Aunque el manifiesto declare `accepts_remote: true`, la política operativa
inicial es **draft-first siempre**:

- Los Claude Code del equipo generan **drafts locales** (`.afp/drafts/`, que va
  en el `.gitignore` del repo del MCP).
- La promoción a un issue de GitLab es un paso **explícito y revisado por un
  humano**: `afp drafts promote <id> --dir <repo> --sink gitlab_issues`.
- Motivo: el contenido de la wiki corporativa es sensible; ningún reporte llega
  a un issue sin que una persona lo revise.
- La redacción/minimización de PII (§5 del spec base) sigue obligatoria; el
  contenido de wiki en `observed`/`evidence` debe minimizarse antes de promover.

## 6. Verificación pendiente en el entorno del trabajo (no bloquea construir)

Se diseña flexible y se confirma mañana con el Claude Code del trabajo:

- Flags y versión exactos de `glab` (`--description` vs `-d`, `--repo` vs `-R`,
  comportamiento de `--yes`, formato de salida de la URL).
- Auth y host: `GITLAB_HOST` + `glab auth login --hostname <host>` con token
  (PAT / project access token) y permisos para crear issues.
- Acceso de red desde donde corre Claude Code hasta el host del GitLab interno.

## 7. Testing

- `tests/test_sinks_gitlab.py`: espejo de `test_sinks_github`, mockeando
  `subprocess.run`. Verifica: comando `glab issue create` bien formado (repo,
  label, title, description), inyección de `GITLAB_HOST` cuando hay `host`,
  retorno de la URL, y `RuntimeError` en fallo/timeout. Nunca llama a `glab` real.
- `tests/test_manifest.py`: el enum acepta `gitlab_issues`; un manifiesto
  `gitlab_issues` sin `repo` falla con `ManifestInvalid`.
- `tests/test_routing.py`: un reporte con subject base coincidente + sink
  `gitlab_issues` se enruta; un subject de otro dueño se bloquea (anti-spoofing).

## 8. Alcance / decisiones

| Decisión | Razón |
|----------|-------|
| Sink vía `glab` CLI, no API REST | Encaja con el flujo actual (auth glab ya hecho); espejo del sink github. YAGNI con la API. |
| `host` en el manifiesto, no hardcodeado | Soporta cualquier GitLab self-hosted sin tocar código. |
| Draft-first incluso con `accepts_remote: true` | Contenido de wiki corporativa sensible; promoción humana revisada. |
| Reutilizar anti-spoofing por base | Ya implementado; cubre `gitlab_issues` sin cambios. |
| Resolver y API REST fuera de alcance | Sub-proyecto 2 / futuro; mantener este entregable pequeño y desplegable mañana. |
