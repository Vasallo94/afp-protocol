import json

from typer.testing import CliRunner

from afp.cli import app


runner = CliRunner()


def test_init_writes_valid_github_manifest(tmp_path) -> None:
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


def test_init_refuses_existing_manifest_without_force(tmp_path) -> None:
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


def test_init_force_overwrites_existing_manifest(tmp_path) -> None:
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
    manifest = json.loads((tmp_path / "afp.json").read_text(encoding="utf-8"))
    assert manifest["subject_uri"] == "mcp://github.com/acme/weather-mcp"


def test_init_requires_repo_for_github_sink(tmp_path) -> None:
    result = runner.invoke(app, [
        "init",
        "--dir", str(tmp_path),
        "--subject", "mcp://github.com/acme/weather-mcp",
        "--sink", "github_issues",
    ])

    assert result.exit_code != 0
    assert "--repo" in result.output
