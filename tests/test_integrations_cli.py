from typer.testing import CliRunner

from afp.cli import app


runner = CliRunner()


def test_integrations_list_shows_supported_integrations(tmp_path) -> None:
    result = runner.invoke(app, ["integrations", "list"], env={"HOME": str(tmp_path)})

    assert result.exit_code == 0, result.output
    assert "codex" in result.output
    assert "claude-code" in result.output
    assert "cursor" in result.output
    assert "generic" in result.output


def test_install_codex_global_copies_skill(tmp_path) -> None:
    result = runner.invoke(
        app,
        ["integrations", "install", "codex", "--global"],
        env={"HOME": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    skill = tmp_path / ".codex" / "skills" / "afp-report" / "SKILL.md"
    assert skill.exists()
    assert "name: afp-report" in skill.read_text(encoding="utf-8")


def test_install_claude_code_global_copies_skill(tmp_path) -> None:
    result = runner.invoke(
        app,
        ["integrations", "install", "claude-code", "--global"],
        env={"HOME": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    skill = tmp_path / ".claude" / "skills" / "afp-report" / "SKILL.md"
    assert skill.exists()
    assert "name: afp-report" in skill.read_text(encoding="utf-8")


def test_install_cursor_project_copies_rule(tmp_path) -> None:
    result = runner.invoke(
        app,
        ["integrations", "install", "cursor", "--project", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    rule = tmp_path / ".cursor" / "rules" / "afp-report.mdc"
    assert rule.exists()
    assert "AFP" in rule.read_text(encoding="utf-8")


def test_install_generic_requires_out() -> None:
    result = runner.invoke(app, ["integrations", "install", "generic"])

    assert result.exit_code != 0
    assert "--out" in result.output


def test_install_generic_writes_prompt_block(tmp_path) -> None:
    out = tmp_path / "AFP-INSTRUCTIONS.md"

    result = runner.invoke(app, ["integrations", "install", "generic", "--out", str(out)])

    assert result.exit_code == 0, result.output
    assert out.exists()
    assert "AFP integration block" in out.read_text(encoding="utf-8")


def test_install_existing_destination_requires_force(tmp_path) -> None:
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


def test_install_force_creates_backup(tmp_path) -> None:
    target = tmp_path / ".codex" / "skills" / "afp-report"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("custom", encoding="utf-8")

    result = runner.invoke(
        app,
        ["integrations", "install", "codex", "--global", "--force"],
        env={"HOME": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    backup = target.with_name("afp-report.bak") / "SKILL.md"
    assert backup.read_text(encoding="utf-8") == "custom"
    assert "name: afp-report" in (target / "SKILL.md").read_text(encoding="utf-8")
