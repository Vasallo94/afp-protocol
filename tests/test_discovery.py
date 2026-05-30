import json

from afp.discovery import discover, RoutingDecision


def test_no_manifest_returns_local_and_draft_only(tmp_path):
    decision = discover(tmp_path)
    assert isinstance(decision, RoutingDecision)
    assert decision.has_manifest is False
    assert decision.manifest is None
    assert set(decision.allowed_sinks) == {"local", "draft"}


def test_root_manifest_allows_declared_remote(tmp_path):
    (tmp_path / "afp.json").write_text(json.dumps({
        "afp_version": "0.2",
        "subject_uri": "mcp://github.com/user/repo",
        "sink": {"type": "github_issues", "repo": "user/repo", "label": "afp-report"},
        "accepts_remote": True,
    }))
    decision = discover(tmp_path)
    assert decision.has_manifest is True
    assert "github_issues" in decision.allowed_sinks
    assert "local" in decision.allowed_sinks


def test_well_known_manifest_is_found(tmp_path):
    wk = tmp_path / ".well-known"
    wk.mkdir()
    (wk / "afp.json").write_text(json.dumps({
        "afp_version": "0.2",
        "subject_uri": "https://api.example.com",
        "sink": {"type": "github_issues", "repo": "user/example", "label": "afp-report"},
        "accepts_remote": True,
    }))
    decision = discover(tmp_path)
    assert decision.has_manifest is True
    assert "github_issues" in decision.allowed_sinks


def test_manifest_without_accepts_remote_blocks_remote(tmp_path):
    (tmp_path / "afp.json").write_text(json.dumps({
        "afp_version": "0.2",
        "subject_uri": "mcp://github.com/user/repo",
        "sink": {"type": "github_issues", "repo": "user/repo"},
        "accepts_remote": False,
    }))
    decision = discover(tmp_path)
    assert set(decision.allowed_sinks) == {"local", "draft"}
