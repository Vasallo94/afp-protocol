import json

from afp.discovery import discover
from afp.sinks import route
from afp.validate import validate_report


def test_full_flow_no_manifest_lands_in_draft(tmp_path, minimal_report):
    validate_report(minimal_report)
    decision = discover(tmp_path)
    assert decision.allowed_sinks == ["local", "draft"]
    sink = route(None, decision, base_dir=tmp_path)
    ref = sink.submit(minimal_report)
    assert ref.startswith("draft:")
    drafts = list((tmp_path / ".afp" / "drafts").glob("*.json"))
    assert len(drafts) == 1
    assert json.loads(drafts[0].read_text())["subject_uri"] == "pkg:pypi/ruff"


def test_full_flow_with_manifest_allows_local(tmp_path, minimal_report):
    (tmp_path / "afp.json").write_text(json.dumps({
        "afp_version": "0.2",
        "subject_uri": "pkg:pypi/ruff",
        "sink": {"type": "github_issues", "repo": "astral-sh/ruff", "label": "afp-report"},
        "accepts_remote": True,
    }))
    decision = discover(tmp_path)
    assert "github_issues" in decision.allowed_sinks
    sink = route("local", decision, base_dir=tmp_path)
    ref = sink.submit(minimal_report)
    assert ref.startswith("local:")
    assert (tmp_path / ".afp" / "reports.jsonl").exists()
