import json

from typer.testing import CliRunner

from afp.cli import app

runner = CliRunner()


def _partial(**extra):
    base = {
        "subject_uri": "pkg:pypi/ruff",
        "goal": "lintear",
        "expectation": "salida JSON",
        "observed": "texto plano",
        "friction_type": "wrong_output",
        "fault_domain": "tool",
        "severity": "degraded",
    }
    base.update(extra)
    return base


def test_report_builds_valid_report(tmp_path):
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(_partial()))
    out = tmp_path / "report.json"
    result = runner.invoke(app, ["report", "--from", str(src), "--out", str(out)])
    assert result.exit_code == 0, result.output
    report = json.loads(out.read_text())
    assert report["report_id"].startswith("afp_")
    assert report["schema_version"] == "afp/0.2"


def test_validate_ok(tmp_path):
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(_partial()))
    out = tmp_path / "report.json"
    runner.invoke(app, ["report", "--from", str(src), "--out", str(out)])
    result = runner.invoke(app, ["validate", str(out)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_report_rejects_secret(tmp_path):
    # El secreto debe bloquearse YA en `report`, que no escribe el fichero.
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(_partial(workaround="ghp_0123456789abcdefghijklmnopqrstuvwxyz")))
    out = tmp_path / "report.json"
    result = runner.invoke(app, ["report", "--from", str(src), "--out", str(out)])
    assert result.exit_code != 0
    assert "ERROR" in result.output
    assert not out.exists()


def test_submit_without_manifest_goes_to_draft(tmp_path):
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(_partial()))
    out = tmp_path / "report.json"
    runner.invoke(app, ["report", "--from", str(src), "--out", str(out)])
    result = runner.invoke(
        app, ["submit", str(out), "--dir", str(tmp_path), "--sink", "github_issues"]
    )
    assert result.exit_code != 0
    assert "no permitido" in result.output.lower() or "not allowed" in result.output.lower()


def test_submit_local_ok(tmp_path):
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(_partial()))
    out = tmp_path / "report.json"
    runner.invoke(app, ["report", "--from", str(src), "--out", str(out)])
    result = runner.invoke(app, ["submit", str(out), "--dir", str(tmp_path), "--sink", "local"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".afp" / "reports.jsonl").exists()
