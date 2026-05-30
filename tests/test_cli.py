import json
from pathlib import Path

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


def test_dogfood_creates_draft_for_afp_itself(tmp_path):
    result = runner.invoke(app, [
        "dogfood",
        "--goal", "probar AFP sobre AFP",
        "--expectation", "el comando debería generar un reporte local",
        "--observed", "necesitaba una forma directa de reportar fricción",
        "--friction-type", "missing_capability",
        "--fault-domain", "tool",
        "--severity", "degraded",
        "--dir", str(tmp_path),
    ])
    assert result.exit_code == 0, result.output
    drafts = list((tmp_path / ".afp" / "drafts").glob("*.json"))
    assert len(drafts) == 1
    report = json.loads(drafts[0].read_text())
    assert report["subject_uri"] == "pkg:github/Vasallo94/afp-protocol@0.2.0"
    assert report["harness"] == "afp-cli"
    assert report["tool_call_name"] == "afp dogfood"


def test_dogfood_rejects_pii_and_writes_no_draft(tmp_path):
    result = runner.invoke(app, [
        "dogfood",
        "--goal", "probar AFP sobre AFP",
        "--expectation", "el comando debería bloquear PII",
        "--observed", "falló con el usuario persona@example.com",
        "--friction-type", "bug",
        "--fault-domain", "tool",
        "--severity", "blocked",
        "--dir", str(tmp_path),
    ])
    assert result.exit_code != 0
    assert "ERROR" in result.output
    assert not (tmp_path / ".afp" / "drafts").exists()


def test_dogfood_help_shows_enum_values():
    result = runner.invoke(app, ["dogfood", "--help"], terminal_width=200)

    assert result.exit_code == 0, result.output
    assert "missing_capability" in result.output
    assert "agent_misuse" in result.output
    assert "degraded" in result.output


def test_validate_manifest_ok(tmp_path):
    manifest = tmp_path / "afp.json"
    manifest.write_text(json.dumps({
        "afp_version": "0.2",
        "subject_uri": "mcp://github.com/Vasallo94/obsidian-mcp-server",
        "sink": {
            "type": "github_issues",
            "repo": "Vasallo94/obsidian-mcp-server",
            "label": "afp-report",
        },
        "redaction": "required",
        "accepts_remote": True,
    }))

    result = runner.invoke(app, ["validate-manifest", str(manifest)])

    assert result.exit_code == 0, result.output
    assert "OK" in result.output


def test_repo_manifest_matches_dogfood_subject():
    manifest = json.loads(Path("afp.json").read_text(encoding="utf-8"))

    assert manifest == {
        "afp_version": "0.2",
        "subject_uri": "pkg:github/Vasallo94/afp-protocol@0.2.0",
        "sink": {
            "type": "github_issues",
            "repo": "Vasallo94/afp-protocol",
            "label": "afp-report",
        },
        "redaction": "required",
        "accepts_remote": True,
        "schema_extensions": [],
    }


def test_validate_manifest_rejects_invalid_manifest(tmp_path):
    manifest = tmp_path / "afp.json"
    manifest.write_text(json.dumps({
        "afp_version": "0.2",
        "subject_uri": "not-a-uri",
        "sink": {"type": "github_issues"},
    }))

    result = runner.invoke(app, ["validate-manifest", str(manifest)])

    assert result.exit_code != 0
    assert "INVALID" in result.output
