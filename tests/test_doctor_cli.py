import json

from typer.testing import CliRunner

from afp.cli import app


runner = CliRunner()


def test_doctor_reports_missing_manifest_and_integrations(tmp_path) -> None:
    result = runner.invoke(app, ["doctor", "--dir", str(tmp_path)], env={"HOME": str(tmp_path)})

    assert result.exit_code == 0, result.output
    assert "OK      CLI:" in result.output
    assert "MISSING manifest:" in result.output
    assert "MISSING codex skill:" in result.output


def test_doctor_reports_valid_manifest_and_pending_drafts(tmp_path) -> None:
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
