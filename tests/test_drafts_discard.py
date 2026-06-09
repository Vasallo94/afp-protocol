"""`afp drafts discard`: cierra el ciclo de revisión para drafts obsoletos.

Caso de uso (draft afp_3b53eb61): un revisor (humano o agente) verifica que la
fricción reportada ya está resuelta en la tool, o que el issue promovido se
cerró, y descarta el draft dejando constancia de por qué en un ledger local
(`.afp/discarded.json`).
"""
import json
from pathlib import Path

from typer.testing import CliRunner

from afp.cli import app

runner = CliRunner()


def _deposit_draft(tmp_path: Path) -> str:
    partial = {
        "subject_uri": "pkg:pypi/ruff",
        "goal": "lintear",
        "expectation": "salida JSON",
        "observed": "texto plano",
        "friction_type": "wrong_output",
        "fault_domain": "tool",
        "severity": "degraded",
    }
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(partial))
    result = runner.invoke(
        app, ["report", "--from", str(src), "--submit", "--dir", str(tmp_path), "--sink", "draft"]
    )
    assert result.exit_code == 0, result.output
    drafts = list((tmp_path / ".afp" / "drafts").glob("*.json"))
    assert len(drafts) == 1
    return json.loads(drafts[0].read_text())["report_id"]


def test_discard_removes_draft_and_records_reason(tmp_path):
    report_id = _deposit_draft(tmp_path)
    result = runner.invoke(
        app,
        ["drafts", "discard", report_id, "--dir", str(tmp_path),
         "--reason", "verified fixed: la tool ya degrada con warning"],
    )
    assert result.exit_code == 0, result.output
    assert report_id in result.output
    assert list((tmp_path / ".afp" / "drafts").glob("*.json")) == []
    ledger = json.loads((tmp_path / ".afp" / "discarded.json").read_text())
    assert ledger[report_id]["reason"] == "verified fixed: la tool ya degrada con warning"
    assert "discarded_at" in ledger[report_id]


def test_discard_requires_reason(tmp_path):
    report_id = _deposit_draft(tmp_path)
    result = runner.invoke(app, ["drafts", "discard", report_id, "--dir", str(tmp_path)])
    assert result.exit_code != 0
    # el draft sigue intacto
    assert len(list((tmp_path / ".afp" / "drafts").glob("*.json"))) == 1


def test_discard_unknown_draft_fails(tmp_path):
    result = runner.invoke(
        app,
        ["drafts", "discard", "afp_nope", "--dir", str(tmp_path), "--reason", "x"],
    )
    assert result.exit_code == 1
    assert "afp_nope" in result.output


def test_discard_accumulates_ledger_entries(tmp_path):
    first = _deposit_draft(tmp_path)
    runner.invoke(app, ["drafts", "discard", first, "--dir", str(tmp_path), "--reason", "uno"])
    second = _deposit_draft(tmp_path)
    runner.invoke(app, ["drafts", "discard", second, "--dir", str(tmp_path), "--reason", "dos"])
    ledger = json.loads((tmp_path / ".afp" / "discarded.json").read_text())
    assert set(ledger) == {first, second}
