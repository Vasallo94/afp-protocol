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


def test_route_allows_remote_with_subtool_fragment(tmp_path):
    # El #fragment identifica una sub-tool del subject que el manifest posee.
    manifest = _manifest()  # subject mcp://github.com/user/repo
    decision = RoutingDecision(True, manifest, ["local", "draft", "github_issues"])
    report = {"subject_uri": "mcp://github.com/user/repo#some_tool", "goal": "g"}
    sink = route("github_issues", decision, report, base_dir=tmp_path)
    assert isinstance(sink, GitHubIssuesSink)


def test_route_allows_remote_ignoring_purl_version(tmp_path):
    # La versión PURL no cambia la propiedad del paquete.
    manifest = Manifest(
        afp_version="0.2", subject_uri="pkg:github/user/repo@0.2.0",
        sink={"type": "github_issues", "repo": "user/repo", "label": "afp-report"},
        accepts_remote=True,
    )
    decision = RoutingDecision(True, manifest, ["local", "draft", "github_issues"])
    report = {"subject_uri": "pkg:github/user/repo@0.3.0", "goal": "g"}
    sink = route("github_issues", decision, report, base_dir=tmp_path)
    assert isinstance(sink, GitHubIssuesSink)


def test_route_still_blocks_different_owner_with_fragment(tmp_path):
    # Un subject de OTRO dueño tiene otra base y sigue bloqueándose,
    # aunque lleve un #fragment.
    manifest = _manifest()  # subject mcp://github.com/user/repo
    decision = RoutingDecision(True, manifest, ["local", "draft", "github_issues"])
    report = {"subject_uri": "mcp://github.com/attacker/other#some_tool", "goal": "g"}
    with pytest.raises(SinkNotAllowed):
        route("github_issues", decision, report, base_dir=tmp_path)


def _http_manifest(subject="https://api.acme.com/v1"):
    return Manifest(
        afp_version="0.2", subject_uri=subject,
        sink={"type": "github_issues", "repo": "acme/api", "label": "afp-report"},
        accepts_remote=True,
    )


def test_route_http_allows_subpath_same_host(tmp_path):
    # Un API HTTP posee todo lo que cuelga de su host/prefijo: /v1/charges es suyo.
    decision = RoutingDecision(True, _http_manifest(), ["local", "draft", "github_issues"])
    report = {"subject_uri": "https://api.acme.com/v1/charges", "goal": "g"}
    sink = route("github_issues", decision, report, base_dir=tmp_path)
    assert isinstance(sink, GitHubIssuesSink)


def test_route_http_ignores_trailing_slash_and_query(tmp_path):
    decision = RoutingDecision(
        True, _http_manifest("https://api.acme.com"), ["local", "draft", "github_issues"]
    )
    report = {"subject_uri": "https://api.acme.com/v1/charges/?x=1", "goal": "g"}
    sink = route("github_issues", decision, report, base_dir=tmp_path)
    assert isinstance(sink, GitHubIssuesSink)


def test_route_http_blocks_lookalike_host(tmp_path):
    # Ataque clásico de prefijo: api.acme.com.evil.com NO es api.acme.com.
    decision = RoutingDecision(
        True, _http_manifest("https://api.acme.com"), ["local", "draft", "github_issues"]
    )
    report = {"subject_uri": "https://api.acme.com.evil.com/v1", "goal": "g"}
    with pytest.raises(SinkNotAllowed):
        route("github_issues", decision, report, base_dir=tmp_path)


def test_route_http_blocks_different_path_prefix(tmp_path):
    # Host multi-tenant: un manifest scoped a /v1/acme no posee /v1/other.
    decision = RoutingDecision(
        True, _http_manifest("https://api.acme.com/v1/acme"),
        ["local", "draft", "github_issues"],
    )
    report = {"subject_uri": "https://api.acme.com/v1/other", "goal": "g"}
    with pytest.raises(SinkNotAllowed):
        route("github_issues", decision, report, base_dir=tmp_path)


def _gitlab_manifest():
    return Manifest(
        afp_version="0.2", subject_uri="mcp://gl.local/grp/proj",
        sink={"type": "gitlab_issues", "host": "gl.local", "repo": "grp/proj",
              "label": "afp-report"},
        accepts_remote=True,
    )


def test_get_sink_gitlab(tmp_path):
    from afp.sinks.gitlab import GitLabIssuesSink
    sink = get_sink("gitlab_issues", base_dir=tmp_path, manifest=_gitlab_manifest())
    assert isinstance(sink, GitLabIssuesSink)
    assert sink.repo == "grp/proj"
    assert sink.host == "gl.local"


def test_route_gitlab_allows_matching_base(tmp_path):
    from afp.sinks.gitlab import GitLabIssuesSink
    decision = RoutingDecision(True, _gitlab_manifest(), ["local", "draft", "gitlab_issues"])
    report = {"subject_uri": "mcp://gl.local/grp/proj#some_tool", "goal": "g"}
    sink = route("gitlab_issues", decision, report, base_dir=tmp_path)
    assert isinstance(sink, GitLabIssuesSink)


def test_route_gitlab_blocks_other_owner(tmp_path):
    decision = RoutingDecision(True, _gitlab_manifest(), ["local", "draft", "gitlab_issues"])
    report = {"subject_uri": "mcp://gl.local/attacker/other#tool", "goal": "g"}
    with pytest.raises(SinkNotAllowed):
        route("gitlab_issues", decision, report, base_dir=tmp_path)
