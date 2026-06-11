# AFP Integration Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add package-first AFP onboarding commands so users can install harness integrations, initialize `afp.json`, and diagnose their setup without cloning `afp-protocol`.

**Architecture:** Keep `src/afp/cli.py` as the Typer surface and move reusable onboarding logic into focused modules. Package integration assets under `src/afp/integrations/`, install them with copy-by-default semantics, and use tests to keep source assets under `integrations/` synchronized with packaged resources.

**Tech Stack:** Python 3.11+, Typer, `importlib.resources`, pytest, existing AFP manifest/discovery/validation modules.

---

### Task 1: Package Integration Assets

**Files:**
- Create: `src/afp/integrations/codex/afp-report/SKILL.md`
- Create: `src/afp/integrations/claude-code/afp-report/SKILL.md`
- Create: `src/afp/integrations/cursor/afp-report.mdc`
- Create: `src/afp/integrations/generic/AFP-INSTRUCTIONS.md`
- Create: `tests/test_integration_assets.py`

- [ ] **Step 1: Write the failing sync/resource tests**

Create `tests/test_integration_assets.py`:

```python
from importlib.resources import files
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_packaged_claude_code_skill_matches_source():
    source = ROOT / "integrations" / "claude-code" / "afp-report" / "SKILL.md"
    packaged = files("afp").joinpath(
        "integrations", "claude-code", "afp-report", "SKILL.md"
    )

    assert packaged.read_text(encoding="utf-8") == _text(source)


def test_packaged_cursor_rule_matches_source():
    source = ROOT / "integrations" / "cursor" / "afp-report.mdc"
    packaged = files("afp").joinpath("integrations", "cursor", "afp-report.mdc")

    assert packaged.read_text(encoding="utf-8") == _text(source)


def test_packaged_generic_block_matches_source():
    source = ROOT / "integrations" / "generic" / "AFP-INSTRUCTIONS.md"
    packaged = files("afp").joinpath("integrations", "generic", "AFP-INSTRUCTIONS.md")

    assert packaged.read_text(encoding="utf-8") == _text(source)


def test_packaged_codex_skill_exists_and_mentions_codex():
    packaged = files("afp").joinpath("integrations", "codex", "afp-report", "SKILL.md")

    text = packaged.read_text(encoding="utf-8")

    assert "name: afp-report" in text
    assert "~/.codex/skills/afp-report" in text
    assert "Codex" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_integration_assets.py -v`

Expected: FAIL because `src/afp/integrations/...` does not exist yet.

- [ ] **Step 3: Add packaged assets**

Create directories under `src/afp/integrations/` and copy:

```bash
mkdir -p src/afp/integrations/claude-code/afp-report
mkdir -p src/afp/integrations/cursor
mkdir -p src/afp/integrations/generic
mkdir -p src/afp/integrations/codex/afp-report
cp integrations/claude-code/afp-report/SKILL.md src/afp/integrations/claude-code/afp-report/SKILL.md
cp integrations/cursor/afp-report.mdc src/afp/integrations/cursor/afp-report.mdc
cp integrations/generic/AFP-INSTRUCTIONS.md src/afp/integrations/generic/AFP-INSTRUCTIONS.md
```

Create `src/afp/integrations/codex/afp-report/SKILL.md` by adapting the Claude Code skill. Required Codex-specific strings:

```markdown
---
name: afp-report
description: File an AFP (Agent Feedback Protocol) field report when a tool you used misbehaved — a bug, undocumented behavior, missing capability, confusing interface, or wrong output that broke or degraded your plan. Use after you hit real tool friction (especially if you needed a workaround), when the user asks to "report this friction", "reporta esta fricción", or "file an AFP report", or when reviewing/verifying existing AFP drafts (AFP-REVIEW signal, "revisa los drafts"). Reports land as local drafts for human review; nothing is sent anywhere automatically.
---

# Filing an AFP field report from Codex
```

Keep the same draft-first workflow as the Claude Code skill, but replace Claude-specific references with Codex:

```json
"harness": "codex"
```

And include the install hint:

```bash
afp integrations install codex --global
```

- [ ] **Step 4: Run asset tests**

Run: `uv run pytest tests/test_integration_assets.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/afp/integrations tests/test_integration_assets.py
git commit -m "feat(integrations): package harness integration assets"
```

### Task 2: Implement Integration Registry and Installer

**Files:**
- Create: `src/afp/integration_manager.py`
- Modify: `src/afp/cli.py`
- Test: `tests/test_integrations_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_integrations_cli.py`:

```python
from pathlib import Path

from typer.testing import CliRunner

from afp.cli import app


runner = CliRunner()


def test_integrations_list_shows_supported_integrations(tmp_path):
    result = runner.invoke(app, ["integrations", "list"], env={"HOME": str(tmp_path)})

    assert result.exit_code == 0, result.output
    assert "codex" in result.output
    assert "claude-code" in result.output
    assert "cursor" in result.output
    assert "generic" in result.output


def test_install_codex_global_copies_skill(tmp_path):
    result = runner.invoke(
        app,
        ["integrations", "install", "codex", "--global"],
        env={"HOME": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    skill = tmp_path / ".codex" / "skills" / "afp-report" / "SKILL.md"
    assert skill.exists()
    assert "name: afp-report" in skill.read_text(encoding="utf-8")


def test_install_claude_code_global_copies_skill(tmp_path):
    result = runner.invoke(
        app,
        ["integrations", "install", "claude-code", "--global"],
        env={"HOME": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    skill = tmp_path / ".claude" / "skills" / "afp-report" / "SKILL.md"
    assert skill.exists()
    assert "name: afp-report" in skill.read_text(encoding="utf-8")


def test_install_cursor_project_copies_rule(tmp_path):
    result = runner.invoke(
        app,
        ["integrations", "install", "cursor", "--project", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    rule = tmp_path / ".cursor" / "rules" / "afp-report.mdc"
    assert rule.exists()
    assert "AFP" in rule.read_text(encoding="utf-8")


def test_install_generic_requires_out(tmp_path):
    result = runner.invoke(app, ["integrations", "install", "generic"])

    assert result.exit_code != 0
    assert "--out" in result.output


def test_install_generic_writes_prompt_block(tmp_path):
    out = tmp_path / "AFP-INSTRUCTIONS.md"

    result = runner.invoke(app, ["integrations", "install", "generic", "--out", str(out)])

    assert result.exit_code == 0, result.output
    assert out.exists()
    assert "Agent Feedback Protocol" in out.read_text(encoding="utf-8")


def test_install_existing_destination_requires_force(tmp_path):
    target = tmp_path / ".codex" / "skills" / "afp-report"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("custom", encoding="utf-8")

    result = runner.invoke(
        app,
        ["integrations", "install", "codex", "--global"],
        env={"HOME": str(tmp_path)},
    )

    assert result.exit_code != 0
    assert "already exists" in result.output


def test_install_force_creates_backup(tmp_path):
    target = tmp_path / ".codex" / "skills" / "afp-report"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("custom", encoding="utf-8")

    result = runner.invoke(
        app,
        ["integrations", "install", "codex", "--global", "--force"],
        env={"HOME": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    assert (target.with_name("afp-report.bak") / "SKILL.md").read_text(encoding="utf-8") == "custom"
    assert "name: afp-report" in (target / "SKILL.md").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_integrations_cli.py -v`

Expected: FAIL because the `integrations` command does not exist.

- [ ] **Step 3: Implement `src/afp/integration_manager.py`**

```python
from __future__ import annotations

import filecmp
import shutil
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path


class IntegrationError(ValueError):
    """Raised when an integration install request is invalid."""


@dataclass(frozen=True)
class Integration:
    name: str
    scope: str
    resource_parts: tuple[str, ...]
    relative_destination: tuple[str, ...] | None


INTEGRATIONS: dict[str, Integration] = {
    "codex": Integration(
        name="codex",
        scope="global",
        resource_parts=("integrations", "codex", "afp-report"),
        relative_destination=(".codex", "skills", "afp-report"),
    ),
    "claude-code": Integration(
        name="claude-code",
        scope="global",
        resource_parts=("integrations", "claude-code", "afp-report"),
        relative_destination=(".claude", "skills", "afp-report"),
    ),
    "cursor": Integration(
        name="cursor",
        scope="project",
        resource_parts=("integrations", "cursor", "afp-report.mdc"),
        relative_destination=(".cursor", "rules", "afp-report.mdc"),
    ),
    "generic": Integration(
        name="generic",
        scope="prompt",
        resource_parts=("integrations", "generic", "AFP-INSTRUCTIONS.md"),
        relative_destination=None,
    ),
}


def integration_names() -> list[str]:
    return sorted(INTEGRATIONS)


def resource_path(integration: Integration) -> Path:
    resource = files("afp")
    for part in integration.resource_parts:
        resource = resource.joinpath(part)
    return Path(str(resource))


def destination_for(name: str, *, home: Path, project: Path | None) -> Path | None:
    integration = _get(name)
    if integration.relative_destination is None:
        return None
    base = home if integration.scope == "global" else project
    if base is None:
        raise IntegrationError(f"{name} requires --project PATH")
    return base.joinpath(*integration.relative_destination)


def status_for(name: str, *, home: Path, project: Path | None) -> str:
    destination = destination_for(name, home=home, project=project)
    if destination is None:
        return "available"
    return "installed" if destination.exists() else "missing"


def install_integration(
    name: str,
    *,
    home: Path,
    project: Path | None,
    global_: bool,
    out: Path | None,
    force: bool,
    mode: str = "copy",
) -> Path:
    integration = _get(name)
    if integration.scope == "global" and not global_:
        raise IntegrationError(f"{name} requires --global")
    if integration.scope == "project" and project is None:
        raise IntegrationError(f"{name} requires --project PATH")
    if integration.scope == "prompt":
        if out is None:
            raise IntegrationError("generic requires --out PATH")
        _replace(source, out, force=force, mode=mode)
        return out
    if mode not in {"copy", "symlink"}:
        raise IntegrationError("--mode must be copy or symlink")

    source = resource_path(integration)
    destination = destination_for(name, home=home, project=project)
    assert destination is not None
    _replace(source, destination, force=force, mode=mode)
    return destination


def _replace(source: Path, destination: Path, *, force: bool, mode: str) -> None:
    if destination.exists() or destination.is_symlink():
        if _same_content(source, destination):
            return
        if not force:
            raise IntegrationError(f"destination already exists: {destination}")
        backup = destination.with_name(destination.name + ".bak")
        if backup.exists() or backup.is_symlink():
            if backup.is_dir() and not backup.is_symlink():
                shutil.rmtree(backup)
            else:
                backup.unlink()
        destination.rename(backup)

    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "symlink":
        destination.symlink_to(source, target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def _same_content(source: Path, destination: Path) -> bool:
    if not destination.exists():
        return False
    if source.is_file() and destination.is_file():
        return source.read_bytes() == destination.read_bytes()
    if source.is_dir() and destination.is_dir():
        cmp = filecmp.dircmp(source, destination)
        return not cmp.left_only and not cmp.right_only and not cmp.diff_files
    return False


def _get(name: str) -> Integration:
    try:
        return INTEGRATIONS[name]
    except KeyError as exc:
        raise IntegrationError(f"unknown integration: {name}") from exc
```

- [ ] **Step 4: Wire CLI commands in `src/afp/cli.py`**

Add imports:

```python
from afp.integration_manager import (
    INTEGRATIONS,
    IntegrationError,
    install_integration,
    status_for,
)
```

Add Typer app near `drafts_app`:

```python
integrations_app = typer.Typer(help="Instala y verifica integraciones AFP para harnesses.")
app.add_typer(integrations_app, name="integrations")
```

Add commands:

```python
@integrations_app.command("list")
def integrations_list(
    project: Path | None = typer.Option(None, "--project", help="Proyecto para checks locales"),
):
    """Lista integraciones AFP soportadas y su estado."""
    home = Path.home()
    typer.echo("name\tscope\tstatus")
    for name, integration in sorted(INTEGRATIONS.items()):
        typer.echo(
            f"{name}\t{integration.scope}\t"
            f"{status_for(name, home=home, project=project)}"
        )


@integrations_app.command("install")
def integrations_install(
    name: str = typer.Argument(..., help="Integración: codex, claude-code, cursor"),
    global_: bool = typer.Option(False, "--global", help="Instalar en ubicación global de usuario"),
    project: Path | None = typer.Option(None, "--project", help="Proyecto destino"),
    out: Path | None = typer.Option(None, "--out", help="Fichero destino para bloques prompt"),
    mode: str = typer.Option("copy", "--mode", help="copy o symlink"),
    force: bool = typer.Option(False, "--force", help="Sobrescribir creando .bak"),
):
    """Instala una integración AFP desde recursos empaquetados."""
    try:
        destination = install_integration(
            name,
            home=Path.home(),
            project=project,
            global_=global_,
            out=out,
            force=force,
            mode=mode,
        )
    except IntegrationError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"OK: {name} instalado en {destination}")
```

- [ ] **Step 5: Run integration CLI tests**

Run: `uv run pytest tests/test_integrations_cli.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/afp/cli.py src/afp/integration_manager.py tests/test_integrations_cli.py
git commit -m "feat(cli): install AFP harness integrations"
```

### Task 3: Add `afp init`

**Files:**
- Create: `src/afp/onboarding.py`
- Modify: `src/afp/cli.py`
- Test: `tests/test_init_cli.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_init_cli.py`:

```python
import json

from typer.testing import CliRunner

from afp.cli import app


runner = CliRunner()


def test_init_writes_valid_github_manifest(tmp_path):
    result = runner.invoke(app, [
        "init",
        "--dir", str(tmp_path),
        "--subject", "mcp://github.com/acme/weather-mcp",
        "--sink", "github_issues",
        "--repo", "acme/weather-mcp",
    ])

    assert result.exit_code == 0, result.output
    manifest = json.loads((tmp_path / "afp.json").read_text(encoding="utf-8"))
    assert manifest == {
        "afp_version": "0.2",
        "subject_uri": "mcp://github.com/acme/weather-mcp",
        "sink": {
            "type": "github_issues",
            "repo": "acme/weather-mcp",
            "label": "afp-report",
        },
        "redaction": "required",
        "accepts_remote": True,
        "schema_extensions": [],
    }


def test_init_refuses_existing_manifest_without_force(tmp_path):
    (tmp_path / "afp.json").write_text("{}", encoding="utf-8")

    result = runner.invoke(app, [
        "init",
        "--dir", str(tmp_path),
        "--subject", "mcp://github.com/acme/weather-mcp",
        "--sink", "github_issues",
        "--repo", "acme/weather-mcp",
    ])

    assert result.exit_code != 0
    assert "already exists" in result.output


def test_init_force_overwrites_existing_manifest(tmp_path):
    (tmp_path / "afp.json").write_text("{}", encoding="utf-8")

    result = runner.invoke(app, [
        "init",
        "--dir", str(tmp_path),
        "--subject", "mcp://github.com/acme/weather-mcp",
        "--sink", "github_issues",
        "--repo", "acme/weather-mcp",
        "--force",
    ])

    assert result.exit_code == 0, result.output
    assert json.loads((tmp_path / "afp.json").read_text(encoding="utf-8"))["subject_uri"] == (
        "mcp://github.com/acme/weather-mcp"
    )


def test_init_requires_repo_for_github_sink(tmp_path):
    result = runner.invoke(app, [
        "init",
        "--dir", str(tmp_path),
        "--subject", "mcp://github.com/acme/weather-mcp",
        "--sink", "github_issues",
    ])

    assert result.exit_code != 0
    assert "--repo" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_init_cli.py -v`

Expected: FAIL because `init` does not exist.

- [ ] **Step 3: Implement manifest builder in `src/afp/onboarding.py`**

```python
from __future__ import annotations

import json
from pathlib import Path

from afp.manifest import ManifestInvalid, load_manifest


class OnboardingError(ValueError):
    """Raised when an onboarding command cannot complete safely."""


def build_manifest(
    *,
    subject: str,
    sink: str,
    repo: str | None,
    host: str | None,
    label: str,
) -> dict:
    sink_payload: dict[str, str] = {"type": sink}
    if sink == "github_issues":
        if not repo:
            raise OnboardingError("--repo is required for github_issues")
        sink_payload["repo"] = repo
    elif sink == "gitlab_issues":
        if not repo:
            raise OnboardingError("--repo is required for gitlab_issues")
        if host:
            sink_payload["host"] = host
        sink_payload["repo"] = repo
    else:
        raise OnboardingError("--sink must be github_issues or gitlab_issues")
    sink_payload["label"] = label
    return {
        "afp_version": "0.2",
        "subject_uri": subject,
        "sink": sink_payload,
        "redaction": "required",
        "accepts_remote": True,
        "schema_extensions": [],
    }


def write_manifest(
    *,
    dir_: Path,
    manifest: dict,
    force: bool,
) -> Path:
    target = Path(dir_) / "afp.json"
    if target.exists() and not force:
        raise OnboardingError(f"afp.json already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        load_manifest(target)
    except (ManifestInvalid, OSError, json.JSONDecodeError) as exc:
        raise OnboardingError(f"generated manifest is invalid: {exc}") from exc
    return target
```

- [ ] **Step 4: Wire `afp init` in `src/afp/cli.py`**

Add imports:

```python
from afp.onboarding import OnboardingError, build_manifest, write_manifest
```

Add command:

```python
@app.command("init")
def init_manifest(
    subject: str = typer.Option(..., "--subject", help="AFP subject_uri for this tool/repo"),
    sink: str = typer.Option(..., "--sink", help="Remote sink: github_issues or gitlab_issues"),
    repo: str | None = typer.Option(None, "--repo", help="Remote repo, e.g. owner/name"),
    host: str | None = typer.Option(None, "--host", help="GitLab host for gitlab_issues"),
    label: str = typer.Option("afp-report", "--label", help="Issue label"),
    dir_: Path = typer.Option(Path("."), "--dir", help="Directory where afp.json is written"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing afp.json"),
):
    """Genera un afp.json válido para el repo/tool actual."""
    try:
        manifest = build_manifest(subject=subject, sink=sink, repo=repo, host=host, label=label)
        target = write_manifest(dir_=dir_, manifest=manifest, force=force)
    except OnboardingError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"OK: manifiesto escrito en {target}")
```

- [ ] **Step 5: Run init tests**

Run: `uv run pytest tests/test_init_cli.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/afp/cli.py src/afp/onboarding.py tests/test_init_cli.py
git commit -m "feat(cli): initialize AFP manifests"
```

### Task 4: Add `afp doctor`

**Files:**
- Modify: `src/afp/onboarding.py`
- Modify: `src/afp/cli.py`
- Test: `tests/test_doctor_cli.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_doctor_cli.py`:

```python
import json

from typer.testing import CliRunner

from afp.cli import app


runner = CliRunner()


def test_doctor_reports_missing_manifest_and_integrations(tmp_path):
    result = runner.invoke(app, ["doctor", "--dir", str(tmp_path)], env={"HOME": str(tmp_path)})

    assert result.exit_code == 0, result.output
    assert "OK      CLI:" in result.output
    assert "MISSING manifest:" in result.output
    assert "MISSING codex skill:" in result.output


def test_doctor_reports_valid_manifest_and_pending_drafts(tmp_path):
    (tmp_path / "afp.json").write_text(json.dumps({
        "afp_version": "0.2",
        "subject_uri": "mcp://github.com/acme/weather-mcp",
        "sink": {"type": "github_issues", "repo": "acme/weather-mcp", "label": "afp-report"},
        "redaction": "required",
        "accepts_remote": True,
        "schema_extensions": [],
    }), encoding="utf-8")
    drafts = tmp_path / ".afp" / "drafts"
    drafts.mkdir(parents=True)
    (drafts / "afp_1.json").write_text("{}", encoding="utf-8")

    result = runner.invoke(app, ["doctor", "--dir", str(tmp_path)], env={"HOME": str(tmp_path)})

    assert result.exit_code == 0, result.output
    assert "OK      manifest:" in result.output
    assert "WARN    drafts: 1 pending" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_doctor_cli.py -v`

Expected: FAIL because `doctor` does not exist.

- [ ] **Step 3: Implement doctor checks**

Append to `src/afp/onboarding.py`:

```python
from dataclasses import dataclass

from afp import __version__
from afp.integration_manager import status_for


@dataclass(frozen=True)
class DoctorCheck:
    status: str
    name: str
    detail: str


def doctor_checks(*, dir_: Path, home: Path) -> list[DoctorCheck]:
    checks = [DoctorCheck("OK", "CLI", f"afp {__version__}")]
    manifest_path = Path(dir_) / "afp.json"
    if manifest_path.exists():
        try:
            load_manifest(manifest_path)
        except (ManifestInvalid, OSError, json.JSONDecodeError) as exc:
            checks.append(DoctorCheck("FAIL", "manifest", str(exc)))
        else:
            checks.append(DoctorCheck("OK", "manifest", str(manifest_path)))
    else:
        checks.append(DoctorCheck("MISSING", "manifest", "run afp init"))

    for name in ("codex", "claude-code"):
        status = status_for(name, home=home, project=dir_)
        if status == "installed":
            checks.append(DoctorCheck("OK", f"{name} skill", "installed"))
        else:
            checks.append(
                DoctorCheck(
                    "MISSING",
                    f"{name} skill",
                    f"run afp integrations install {name} --global",
                )
            )

    drafts = list((Path(dir_) / ".afp" / "drafts").glob("*.json"))
    if drafts:
        noun = "pending" if len(drafts) == 1 else "pending"
        checks.append(
            DoctorCheck(
                "WARN",
                "drafts",
                f"{len(drafts)} {noun}, review with afp drafts list --dir {dir_}",
            )
        )
    else:
        checks.append(DoctorCheck("OK", "drafts", "none pending"))
    return checks
```

- [ ] **Step 4: Wire `afp doctor` in `src/afp/cli.py`**

Add import:

```python
from afp.onboarding import OnboardingError, build_manifest, doctor_checks, write_manifest
```

Add command:

```python
@app.command("doctor")
def doctor(
    dir_: Path = typer.Option(Path("."), "--dir", help="Directory to inspect"),
):
    """Comprueba si AFP está listo en el entorno actual."""
    for check in doctor_checks(dir_=dir_, home=Path.home()):
        typer.echo(f"{check.status:<7} {check.name}: {check.detail}")
```

- [ ] **Step 5: Run doctor tests**

Run: `uv run pytest tests/test_doctor_cli.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/afp/cli.py src/afp/onboarding.py tests/test_doctor_cli.py
git commit -m "feat(cli): add AFP setup doctor"
```

### Task 5: Documentation and Full Verification

**Files:**
- Modify: `README.md`
- Modify: `README.es.md`
- Test: full suite

- [ ] **Step 1: Update README integration section**

In `README.md`, replace manual install snippets under "Harness integrations" with:

```markdown
Install AFP once:

```bash
uv tool install git+https://github.com/Vasallo94/afp-protocol
```

Then install the harness integration you use:

```bash
afp integrations install codex --global
afp integrations install claude-code --global
afp integrations install cursor --project .
afp doctor
```

Integrations install from packaged resources; cloning this repository is not required.
Agents emit drafts only. Humans review with `afp drafts list/show` and promote with `afp drafts promote`.
```

- [ ] **Step 2: Update Spanish README with equivalent section**

Add the same command set to `README.es.md` using Spanish prose:

```markdown
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

Las integraciones se copian desde recursos empaquetados; no hace falta clonar este repo.
Los agentes solo emiten drafts. La promoción a issues la decide un humano.
```

- [ ] **Step 3: Run targeted tests**

Run:

```bash
uv run pytest tests/test_integration_assets.py tests/test_integrations_cli.py tests/test_init_cli.py tests/test_doctor_cli.py -v
```

Expected: PASS.

- [ ] **Step 4: Run full quality gate**

Run:

```bash
uv run pytest -q
uv build
```

Expected: PASS. The build should include `src/afp/integrations/...`.

- [ ] **Step 5: Manual smoke test**

Run:

```bash
tmp="$(mktemp -d)"
HOME="$tmp" uv run afp integrations install codex --global
test -f "$tmp/.codex/skills/afp-report/SKILL.md"
uv run afp init --dir "$tmp/project" --subject mcp://github.com/acme/weather-mcp --sink github_issues --repo acme/weather-mcp
HOME="$tmp" uv run afp doctor --dir "$tmp/project"
```

Expected: the `test -f` command exits 0, `afp init` writes a manifest, and `afp doctor` reports CLI and manifest OK.

- [ ] **Step 6: Commit**

```bash
git add README.md README.es.md
git commit -m "docs: document AFP integration onboarding"
```

### Task 6: Final Review

**Files:**
- Review all changed files

- [ ] **Step 1: Inspect git status**

Run: `git status --short`

Expected: clean worktree.

- [ ] **Step 2: Inspect commits**

Run: `git log --oneline -5`

Expected: commits from Tasks 1-5 are present.

- [ ] **Step 3: Summarize implementation**

Report:

- Commands added: `afp integrations list`, `afp integrations install`, `afp init`, `afp doctor`.
- Package-first behavior confirmed.
- Tests/build run results.
