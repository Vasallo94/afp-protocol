# GitLab sink (gitlab_issues) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir un sink `gitlab_issues` que abra issues en un GitLab self-hosted/on-premise vía `glab` CLI, espejo del sink `github_issues` existente.

**Architecture:** Nuevo `GitLabIssuesSink` (mismo patrón que `GitHubIssuesSink`: subprocess al CLI, timeout, manejo de error), inyectando `GITLAB_HOST` cuando el manifiesto declara `host`. Se amplía el JSON Schema del manifiesto (enum + `host` + `repo` condicional) y la factoría `get_sink`. El anti-spoofing ya cubre `gitlab_issues` porque está en `REMOTE_SINKS`.

**Tech Stack:** Python ≥3.11, `glab` CLI (mockeado en tests), `subprocess`, `jsonschema`, `pytest`. Ejecutar tests con `uv run pytest`.

**Spec:** `docs/superpowers/specs/2026-05-31-afp-gitlab-sink-design.md`.

---

## File Structure

```
src/afp/sinks/gitlab.py            # NUEVO: GitLabIssuesSink (espejo de github.py)
src/afp/sinks/__init__.py          # MODIFICAR: rama gitlab_issues en get_sink
src/afp/schema/afp_manifest.schema.json  # MODIFICAR: enum + host + repo condicional
tests/test_sinks_gitlab.py         # NUEVO: tests del sink (subprocess mockeado)
tests/test_manifest.py             # MODIFICAR: aceptar gitlab_issues; exigir repo
tests/test_routing.py              # MODIFICAR: anti-spoofing para gitlab_issues
```

Contexto de APIs existentes (no reimplementar):
- `src/afp/sinks/base.py`: `class Sink` con `name` y `submit(report)->str`.
- `src/afp/sinks/github.py`: `GitHubIssuesSink(repo, label)` — patrón a espejar.
- `src/afp/sinks/__init__.py`: `get_sink(sink_type, *, base_dir, manifest)`, `route(...)`, `REMOTE_SINKS = {"github_issues","gitlab_issues","file","http"}` (ya incluye gitlab).
- `src/afp/manifest.py`: `Manifest(afp_version, subject_uri, sink, redaction, accepts_remote, schema_extensions)`, `load_manifest(path)`, valida contra el schema.

---

### Task 1: GitLabIssuesSink

**Files:**
- Create: `src/afp/sinks/gitlab.py`
- Test: `tests/test_sinks_gitlab.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_sinks_gitlab.py
from unittest.mock import patch
import subprocess

import pytest

from afp.sinks.gitlab import GitLabIssuesSink


def _report():
    return {
        "report_id": "afp_x", "subject_uri": "mcp://gl.local/grp/mcp#tool",
        "friction_type": "bug", "severity": "blocked", "goal": "g",
        "expectation": "e", "observed": "o",
    }


def test_gitlab_sink_calls_glab_and_returns_url():
    sink = GitLabIssuesSink(repo="grp/proj", label="afp-report")
    fake = subprocess.CompletedProcess(
        args=["glab"], returncode=0,
        stdout="https://gl.local/grp/proj/-/issues/7\n", stderr="",
    )
    with patch("afp.sinks.gitlab.subprocess.run", return_value=fake) as run:
        ref = sink.submit(_report())
    assert ref == "https://gl.local/grp/proj/-/issues/7"
    args = run.call_args.args[0]
    assert args[:3] == ["glab", "issue", "create"]
    assert "--repo" in args and "grp/proj" in args
    assert "--label" in args and "afp-report" in args


def test_gitlab_sink_injects_host_env():
    sink = GitLabIssuesSink(repo="grp/proj", host="gl.local")
    fake = subprocess.CompletedProcess(args=["glab"], returncode=0, stdout="url", stderr="")
    with patch("afp.sinks.gitlab.subprocess.run", return_value=fake) as run:
        sink.submit(_report())
    env = run.call_args.kwargs["env"]
    assert env["GITLAB_HOST"] == "gl.local"


def test_gitlab_sink_no_host_passes_no_env():
    sink = GitLabIssuesSink(repo="grp/proj")
    fake = subprocess.CompletedProcess(args=["glab"], returncode=0, stdout="url", stderr="")
    with patch("afp.sinks.gitlab.subprocess.run", return_value=fake) as run:
        sink.submit(_report())
    assert run.call_args.kwargs.get("env") is None


def test_gitlab_sink_raises_on_failure():
    sink = GitLabIssuesSink(repo="grp/proj")
    fake = subprocess.CompletedProcess(args=["glab"], returncode=1, stdout="", stderr="boom")
    with patch("afp.sinks.gitlab.subprocess.run", return_value=fake):
        with pytest.raises(RuntimeError):
            sink.submit(_report())


def test_gitlab_sink_raises_on_timeout():
    sink = GitLabIssuesSink(repo="grp/proj")
    with patch("afp.sinks.gitlab.subprocess.run",
               side_effect=subprocess.TimeoutExpired(cmd=["glab"], timeout=30)):
        with pytest.raises(RuntimeError):
            sink.submit(_report())
```

- [ ] **Step 2: Ejecutar el test y ver que falla**

Run: `uv run pytest tests/test_sinks_gitlab.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'afp.sinks.gitlab'`

- [ ] **Step 3: Escribir `src/afp/sinks/gitlab.py`**

```python
import json
import os
import subprocess

from afp.sinks.base import Sink


class GitLabIssuesSink(Sink):
    name = "gitlab_issues"

    def __init__(self, repo: str, label: str = "afp-report", host: str | None = None):
        self.repo = repo
        self.label = label
        self.host = host

    def _title(self, report: dict) -> str:
        severity = report.get("severity", "unknown")
        goal = str(report.get("goal") or report.get("subject_uri") or "Field report")
        goal = " ".join(goal.split())
        if len(goal) > 80:
            goal = goal[:77].rstrip() + "..."
        return f"[AFP/{severity}] {goal}"

    def _body(self, report: dict) -> str:
        subject = report.get("subject_uri", "unknown")
        friction_type = report.get("friction_type", "unknown")
        fault_domain = report.get("fault_domain", "unknown")
        severity = report.get("severity", "unknown")
        goal = report.get("goal", "")
        expectation = report.get("expectation", "")
        observed = report.get("observed", "")
        workaround = report.get("workaround")
        plan_step = report.get("plan_step")

        sections = [
            "## AFP Field Report",
            "",
            f"- Subject: `{subject}`",
            f"- Type: `{friction_type}`",
            f"- Fault domain: `{fault_domain}`",
            f"- Severity: `{severity}`",
        ]
        if plan_step:
            sections.append(f"- Plan step: {plan_step}")
        sections.extend([
            "",
            "### Goal",
            "",
            str(goal),
            "",
            "### Expected",
            "",
            str(expectation),
            "",
            "### Observed",
            "",
            str(observed),
        ])
        if workaround:
            sections.extend(["", "### Workaround", "", str(workaround)])
        sections.extend([
            "",
            "<details>",
            "<summary>Raw AFP JSON</summary>",
            "",
            "```json",
            json.dumps(report, ensure_ascii=False, indent=2),
            "```",
            "",
            "</details>",
        ])
        return "\n".join(sections)

    def submit(self, report: dict) -> str:
        cmd = [
            "glab", "issue", "create",
            "--repo", self.repo,
            "--title", self._title(report),
            "--description", self._body(report),
            "--label", self.label,
            "--yes",
        ]
        env = {**os.environ, "GITLAB_HOST": self.host} if self.host else None
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, env=env
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("glab issue create excedió el timeout") from exc
        if result.returncode != 0:
            raise RuntimeError(f"glab issue create falló: {result.stderr.strip()}")
        return result.stdout.strip()
```

- [ ] **Step 4: Ejecutar el test y ver que pasa**

Run: `uv run pytest tests/test_sinks_gitlab.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/afp/sinks/gitlab.py tests/test_sinks_gitlab.py
git commit -m "feat: add GitLabIssuesSink via glab CLI (self-hosted host support)"
```

---

### Task 2: Schema del manifiesto acepta gitlab_issues

**Files:**
- Modify: `src/afp/schema/afp_manifest.schema.json`
- Test: `tests/test_manifest.py`

- [ ] **Step 1: Escribir los tests que fallan (añadir a `tests/test_manifest.py`)**

```python
def test_manifest_accepts_gitlab_issues(tmp_path):
    data = _good()
    data["sink"] = {"type": "gitlab_issues", "host": "gl.local",
                    "repo": "grp/proj", "label": "afp-report"}
    p = tmp_path / "afp.json"
    p.write_text(json.dumps(data))
    m = load_manifest(p)
    assert m.sink["type"] == "gitlab_issues"
    assert m.sink["host"] == "gl.local"


def test_manifest_gitlab_issues_requires_repo(tmp_path):
    data = _good()
    data["sink"] = {"type": "gitlab_issues", "host": "gl.local"}  # falta repo
    p = tmp_path / "afp.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ManifestInvalid):
        load_manifest(p)
```

- [ ] **Step 2: Ejecutar y ver que fallan**

Run: `uv run pytest tests/test_manifest.py -k gitlab -v`
Expected: FAIL — `gitlab_issues` no está en el enum (ValidationError → ManifestInvalid) en el primer test, y el segundo no falla como se espera.

- [ ] **Step 3: Modificar `src/afp/schema/afp_manifest.schema.json`**

Cambiar el enum de `sink.type` para incluir `gitlab_issues`:

```json
        "type": {
          "type": "string",
          "enum": ["github_issues", "gitlab_issues", "local", "draft"]
        },
```

Añadir la propiedad `host` dentro de `sink.properties` (junto a `repo`, `label`, `path`, `url`):

```json
        "host": { "type": "string" },
```

Añadir una segunda condición al `allOf` existente (que ya exige `repo` para `github_issues`), para exigir `repo` también con `gitlab_issues`. El `allOf` queda así:

```json
  "allOf": [
    {
      "if": {
        "properties": { "sink": { "properties": { "type": { "const": "github_issues" } } } }
      },
      "then": {
        "properties": { "sink": { "required": ["type", "repo"] } }
      }
    },
    {
      "if": {
        "properties": { "sink": { "properties": { "type": { "const": "gitlab_issues" } } } }
      },
      "then": {
        "properties": { "sink": { "required": ["type", "repo"] } }
      }
    }
  ]
```

- [ ] **Step 4: Ejecutar y ver que pasan (y nada regresiona)**

Run: `uv run pytest tests/test_manifest.py -v`
Expected: PASS (todos, incluidos los dos nuevos)

- [ ] **Step 5: Commit**

```bash
git add src/afp/schema/afp_manifest.schema.json tests/test_manifest.py
git commit -m "feat: manifest schema accepts gitlab_issues sink (host + conditional repo)"
```

---

### Task 3: Wiring en get_sink + routing del anti-spoofing

**Files:**
- Modify: `src/afp/sinks/__init__.py`
- Test: `tests/test_routing.py`

- [ ] **Step 1: Escribir los tests que fallan (añadir a `tests/test_routing.py`)**

```python
def test_get_sink_gitlab(tmp_path):
    from afp.manifest import Manifest
    from afp.sinks.gitlab import GitLabIssuesSink
    manifest = Manifest(
        afp_version="0.2", subject_uri="mcp://gl.local/grp/proj",
        sink={"type": "gitlab_issues", "host": "gl.local", "repo": "grp/proj",
              "label": "afp-report"},
        accepts_remote=True,
    )
    sink = get_sink("gitlab_issues", base_dir=tmp_path, manifest=manifest)
    assert isinstance(sink, GitLabIssuesSink)
    assert sink.repo == "grp/proj"
    assert sink.host == "gl.local"


def test_route_gitlab_allows_matching_base(tmp_path):
    from afp.manifest import Manifest
    from afp.sinks.gitlab import GitLabIssuesSink
    manifest = Manifest(
        afp_version="0.2", subject_uri="mcp://gl.local/grp/proj",
        sink={"type": "gitlab_issues", "host": "gl.local", "repo": "grp/proj"},
        accepts_remote=True,
    )
    decision = RoutingDecision(True, manifest, ["local", "draft", "gitlab_issues"])
    report = {"subject_uri": "mcp://gl.local/grp/proj#some_tool", "goal": "g"}
    sink = route("gitlab_issues", decision, report, base_dir=tmp_path)
    assert isinstance(sink, GitLabIssuesSink)


def test_route_gitlab_blocks_other_owner(tmp_path):
    from afp.manifest import Manifest
    manifest = Manifest(
        afp_version="0.2", subject_uri="mcp://gl.local/grp/proj",
        sink={"type": "gitlab_issues", "host": "gl.local", "repo": "grp/proj"},
        accepts_remote=True,
    )
    decision = RoutingDecision(True, manifest, ["local", "draft", "gitlab_issues"])
    report = {"subject_uri": "mcp://gl.local/attacker/other#tool", "goal": "g"}
    with pytest.raises(SinkNotAllowed):
        route("gitlab_issues", decision, report, base_dir=tmp_path)
```

- [ ] **Step 2: Ejecutar y ver que fallan**

Run: `uv run pytest tests/test_routing.py -k gitlab -v`
Expected: FAIL — `get_sink` no conoce `gitlab_issues` (lanza `ValueError: sink desconocido`).

- [ ] **Step 3: Modificar `src/afp/sinks/__init__.py`**

Añadir el import al principio del fichero (junto a los otros imports de sinks):

```python
from afp.sinks.gitlab import GitLabIssuesSink
```

Añadir la rama en `get_sink`, justo después de la rama de `github_issues`:

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

(`REMOTE_SINKS` ya incluye `gitlab_issues`, así que `route()` aplica el anti-spoofing por base sin más cambios.)

- [ ] **Step 4: Ejecutar y ver que pasan + suite completa**

Run: `uv run pytest tests/test_routing.py -k gitlab -v`
Expected: PASS (3 nuevos)

Run: `uv run pytest -q`
Expected: PASS (toda la suite, ~95 tests)

- [ ] **Step 5: Commit**

```bash
git add src/afp/sinks/__init__.py tests/test_routing.py
git commit -m "feat: wire gitlab_issues into sink factory + routing"
```

---

### Task 4: README — documentar el sink GitLab + plantilla afp.json

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Añadir a `README.md` una sección sobre el sink GitLab**

Insertar tras la sección de uso de la CLI (verbatim):

````markdown
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

Requiere `glab` instalado y autenticado contra el host (`glab auth login --hostname <host>`).
La promoción a issue es explícita y revisada: `afp drafts promote <id> --dir <repo> --sink gitlab_issues`.
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document gitlab_issues sink and afp.json template"
```

---

## Notas para el implementador

- **TDD estricto**: test rojo → impl → verde → commit. No saltes ver el test fallar.
- **DRY pendiente (no en este plan)**: `_body`/`_title` y el `_render_report_markdown` de `cli.py` duplican estructura de Markdown. Aceptable por ahora (espejo del sink github). Unificar en un renderer compartido es un follow-up, no parte de T-01.
- **YAGNI**: no implementar fallback de API REST de GitLab; solo `glab` CLI.
- **Verificación real pendiente** (en el trabajo, no bloquea): flags exactos de `glab` (`--description`, `--yes`, formato de la URL de salida), auth/host. Los tests mockean `subprocess.run`, así que no dependen de `glab` real.
