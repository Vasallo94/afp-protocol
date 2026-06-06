# Draft Review Signal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Al depositar un draft, el CLI emite en stderr una línea `AFP-REVIEW:` que indica cuántos drafts hay pendientes y el comando para revisarlos, sirviendo a la vez al humano y a un harness agéntico.

**Architecture:** Una función pura `review_notice(dir_)` cuenta los `*.json` bajo `.afp/drafts/` y formatea el mensaje (o `None`). Un helper de CLI `_announce_review(dir_)` la imprime en stderr. Los tres comandos que crean drafts (`report --submit`, `submit`, `dogfood`) lo invocan tras un depósito exitoso cuando el sink resuelto fue `draft`. El contrato estable de integración es el prefijo `AFP-REVIEW:`.

**Tech Stack:** Python 3.11+, Typer (CLI), pytest, `typer.testing.CliRunner` (stdout/stderr separados por defecto con el Click vendido).

**Spec:** `docs/superpowers/specs/2026-06-04-afp-draft-review-signal-design.md`

---

## File Structure

- `src/afp/cli.py` — añadir `review_notice` (pura) y `_announce_review` (helper); invocar en `report`, `submit`, `dogfood`. Reutiliza `_draft_paths` ya existente (cuenta `*.json` sin parsear).
- `tests/test_cli.py` — tests unitarios de `review_notice` + integración de canal (stderr/stdout) para las tres rutas y el caso no-draft. Reutiliza `runner` y `_partial`.
- `README.md` — documentar el contrato `AFP-REVIEW:` en la sección de drafts.

---

### Task 1: Función pura `review_notice`

**Files:**
- Modify: `src/afp/cli.py` (añadir función tras `_render_report_markdown`, ~línea 90)
- Test: `tests/test_cli.py` (añadir al final)

- [ ] **Step 1: Write the failing tests**

Añadir a `tests/test_cli.py`:

```python
from afp.cli import review_notice


def test_review_notice_none_when_no_drafts(tmp_path):
    assert review_notice(tmp_path) is None


def test_review_notice_singular(tmp_path):
    drafts = tmp_path / ".afp" / "drafts"
    drafts.mkdir(parents=True)
    (drafts / "afp_1.json").write_text("{}", encoding="utf-8")
    msg = review_notice(tmp_path)
    assert msg.startswith("AFP-REVIEW: 1 draft pendiente")
    assert f"afp drafts list --dir {tmp_path}" in msg


def test_review_notice_plural_counts_all_json_even_invalid(tmp_path):
    drafts = tmp_path / ".afp" / "drafts"
    drafts.mkdir(parents=True)
    (drafts / "afp_1.json").write_text("{}", encoding="utf-8")
    (drafts / "afp_2.json").write_text("no es json válido", encoding="utf-8")
    msg = review_notice(tmp_path)
    assert msg.startswith("AFP-REVIEW: 2 drafts pendientes")
```

> Nota: el render de `--dir` (vía `str(Path(dir_))`) queda cubierto por el assert
> de ruta absoluta en `test_review_notice_singular`. El caso `.` es trivial
> (`str(Path(".")) == "."`) y no merece un test condicional.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -q -k review_notice`
Expected: FAIL con `ImportError: cannot import name 'review_notice'` (o AttributeError).

- [ ] **Step 3: Write minimal implementation**

Añadir en `src/afp/cli.py` justo después de `_render_report_markdown` (línea ~90):

```python
def review_notice(dir_: Path) -> str | None:
    """Mensaje de revisión si hay drafts pendientes; None si no hay.

    Cuenta paths `*.json` bajo `.afp/drafts/` sin parsearlos: un draft inválido
    sigue siendo algo que el humano debe atender. El prefijo `AFP-REVIEW:` es el
    contrato de integración (humano + harness).
    """
    n = len(_draft_paths(dir_))
    if n == 0:
        return None
    noun = "draft pendiente" if n == 1 else "drafts pendientes"
    return (
        f"AFP-REVIEW: {n} {noun} de revisión humana → "
        f"afp drafts list --dir {str(Path(dir_))}"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -q -k review_notice`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/afp/cli.py tests/test_cli.py
git commit -m "feat(cli): review_notice pure helper for pending drafts (#4)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Emitir `AFP-REVIEW:` en las tres rutas que crean drafts

**Files:**
- Modify: `src/afp/cli.py` — añadir `_announce_review`; invocar en `report` (tras OK, ~línea 118), `submit` (tras OK, ~línea 166), `dogfood` (tras OK, ~línea 271)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing integration tests**

Añadir a `tests/test_cli.py`:

```python
def test_dogfood_draft_emits_review_signal_on_stderr(tmp_path):
    result = runner.invoke(app, [
        "dogfood",
        "--goal", "probar AFP sobre AFP",
        "--expectation", "señal de revisión visible",
        "--observed", "antes el draft se creaba en silencio",
        "--friction-type", "missing_capability",
        "--fault-domain", "tool",
        "--severity", "degraded",
        "--dir", str(tmp_path),
    ])
    assert result.exit_code == 0, result.output
    assert "AFP-REVIEW:" in result.stderr
    assert "AFP-REVIEW:" not in result.stdout


def test_submit_draft_emits_review_signal_on_stderr(tmp_path):
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(_partial()))
    out = tmp_path / "report.json"
    runner.invoke(app, ["report", "--from", str(src), "--out", str(out)])
    result = runner.invoke(app, ["submit", str(out), "--dir", str(tmp_path), "--sink", "draft"])
    assert result.exit_code == 0, result.output
    assert "AFP-REVIEW:" in result.stderr
    assert "OK: depositado" in result.stdout


def test_report_submit_draft_emits_review_signal_on_stderr(tmp_path):
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(_partial()))
    result = runner.invoke(app, [
        "report", "--from", str(src), "--submit",
        "--dir", str(tmp_path), "--sink", "draft",
    ])
    assert result.exit_code == 0, result.output
    assert "AFP-REVIEW:" in result.stderr


def test_local_sink_does_not_emit_review_signal(tmp_path):
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(_partial()))
    out = tmp_path / "report.json"
    runner.invoke(app, ["report", "--from", str(src), "--out", str(out)])
    result = runner.invoke(app, ["submit", str(out), "--dir", str(tmp_path), "--sink", "local"])
    assert result.exit_code == 0, result.output
    assert "AFP-REVIEW:" not in result.stderr
    assert "AFP-REVIEW:" not in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -q -k "review_signal"`
Expected: FAIL (los `AFP-REVIEW:` no aparecen porque aún no se invoca el helper).

- [ ] **Step 3: Write minimal implementation**

3a. Añadir el helper en `src/afp/cli.py` justo después de `review_notice`:

```python
def _announce_review(dir_: Path) -> None:
    notice = review_notice(dir_)
    if notice:
        typer.echo(notice, err=True)
```

3b. En el comando `report`, tras `typer.echo(f"OK: depositado vía {sink_name} -> {ref}")`:

```python
        typer.echo(f"OK: depositado vía {sink_name} -> {ref}")
        if sink_name == "draft":
            _announce_review(dir_)
```

3c. En el comando `submit`, tras `typer.echo(f"OK: depositado vía {chosen.name} -> {ref}")`:

```python
    typer.echo(f"OK: depositado vía {chosen.name} -> {ref}")
    if chosen.name == "draft":
        _announce_review(dir_)
```

3d. En `dogfood`, tras `typer.echo(f"OK: dogfood report depositado vía {chosen.name} -> {ref}")`:

```python
    typer.echo(f"OK: dogfood report depositado vía {chosen.name} -> {ref}")
    if chosen.name == "draft":
        _announce_review(dir_)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -q`
Expected: PASS (todos; las 4 integración nuevas + 4 de Task 1 + las 14 previas).

- [ ] **Step 5: Commit**

```bash
git add src/afp/cli.py tests/test_cli.py
git commit -m "feat(cli): emit AFP-REVIEW signal on draft deposit (#4)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Documentar el contrato en el README

**Files:**
- Modify: `README.md` (sección de drafts, tras el bloque `afp drafts ...`, ~línea 40)

- [ ] **Step 1: Update README**

Insertar tras la lista de comandos `afp drafts ...` (después de la línea de `promote`, antes de `partial.json mínimo`):

```markdown
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
```

- [ ] **Step 2: Verify suite still green**

Run: `uv run pytest -q`
Expected: PASS (toda la suite).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document AFP-REVIEW draft signal contract (#4)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- Canal stderr → Task 2 (asserts `result.stderr` / `result.stdout`). ✓
- Solo sink `draft`, 3 rutas, no `_submit_report`/promote → Task 2 (call-sites en `report`/`submit`/`dogfood`; `_submit_report` intacto). ✓
- Orden post-éxito → call-sites tras el `OK:` echo (depósito ya exitoso). ✓
- Contar `*.json` sin parsear, inválidos cuentan → Task 1 (`_draft_paths` + test `even_invalid`). ✓
- `str(Path(dir_))` → Task 1 implementación + assert de ruta en `test_review_notice_singular`. ✓
- Singular/plural → Task 1. ✓
- Tests sobre stderr/stdout, no output → Task 2. ✓
- README como contrato → Task 3. ✓

**Placeholder scan:** sin TBD/TODO; todo el código está completo.

**Type consistency:** `review_notice(dir_) -> str | None` y `_announce_review(dir_) -> None` usados consistentemente; `_draft_paths` ya existe en `cli.py`.
