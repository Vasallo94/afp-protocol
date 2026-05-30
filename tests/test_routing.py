import pytest

from afp.discovery import RoutingDecision
from afp.manifest import Manifest
from afp.sinks import get_sink, route, SinkNotAllowed
from afp.sinks.local import LocalSink
from afp.sinks.github import GitHubIssuesSink


def test_get_sink_local(tmp_path):
    sink = get_sink("local", base_dir=tmp_path)
    assert isinstance(sink, LocalSink)


def test_get_sink_unknown_raises():
    with pytest.raises(ValueError):
        get_sink("carrier_pigeon")


def test_route_blocks_remote_without_manifest(tmp_path):
    decision = RoutingDecision(has_manifest=False, manifest=None, allowed_sinks=["local", "draft"])
    with pytest.raises(SinkNotAllowed):
        route("github_issues", decision, base_dir=tmp_path)


def _manifest():
    return Manifest(
        afp_version="0.2", subject_uri="mcp://github.com/user/repo",
        sink={"type": "github_issues", "repo": "user/repo", "label": "afp-report"},
        accepts_remote=True,
    )


def test_route_allows_remote_with_manifest_and_matching_subject(tmp_path):
    manifest = _manifest()
    decision = RoutingDecision(True, manifest, ["local", "draft", "github_issues"])
    report = {"subject_uri": "mcp://github.com/user/repo", "goal": "g"}
    sink = route("github_issues", decision, report, base_dir=tmp_path)
    assert isinstance(sink, GitHubIssuesSink)
    assert sink.repo == "user/repo"


def test_route_blocks_subject_uri_spoofing(tmp_path):
    manifest = _manifest()
    decision = RoutingDecision(True, manifest, ["local", "draft", "github_issues"])
    report = {"subject_uri": "mcp://github.com/attacker/other", "goal": "g"}
    with pytest.raises(SinkNotAllowed):
        route("github_issues", decision, report, base_dir=tmp_path)


def test_route_blocks_remote_without_report(tmp_path):
    manifest = _manifest()
    decision = RoutingDecision(True, manifest, ["local", "draft", "github_issues"])
    with pytest.raises(SinkNotAllowed):
        route("github_issues", decision, None, base_dir=tmp_path)


def test_route_defaults_to_draft_when_none_requested(tmp_path):
    decision = RoutingDecision(False, None, ["local", "draft"])
    sink = route(None, decision, base_dir=tmp_path)
    assert sink.name == "draft"
