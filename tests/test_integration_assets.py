from importlib.resources import files
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_packaged_claude_code_skill_matches_source() -> None:
    source = ROOT / "integrations" / "claude-code" / "afp-report" / "SKILL.md"
    packaged = files("afp").joinpath(
        "integrations", "claude-code", "afp-report", "SKILL.md"
    )

    assert packaged.read_text(encoding="utf-8") == _text(source)


def test_packaged_cursor_rule_matches_source() -> None:
    source = ROOT / "integrations" / "cursor" / "afp-report.mdc"
    packaged = files("afp").joinpath("integrations", "cursor", "afp-report.mdc")

    assert packaged.read_text(encoding="utf-8") == _text(source)


def test_packaged_generic_block_matches_source() -> None:
    source = ROOT / "integrations" / "generic" / "AFP-INSTRUCTIONS.md"
    packaged = files("afp").joinpath("integrations", "generic", "AFP-INSTRUCTIONS.md")

    assert packaged.read_text(encoding="utf-8") == _text(source)


def test_packaged_codex_skill_exists_and_mentions_codex() -> None:
    packaged = files("afp").joinpath("integrations", "codex", "afp-report", "SKILL.md")

    text = packaged.read_text(encoding="utf-8")

    assert "name: afp-report" in text
    assert "~/.codex/skills/afp-report" in text
    assert "Codex" in text
