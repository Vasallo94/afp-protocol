from unittest.mock import patch
import subprocess

import pytest

from afp.sinks.github import GitHubIssuesSink


def test_github_sink_calls_gh_and_returns_url():
    sink = GitHubIssuesSink(repo="user/repo", label="afp-report")
    fake = subprocess.CompletedProcess(
        args=["gh"], returncode=0,
        stdout="https://github.com/user/repo/issues/42\n", stderr="",
    )
    with patch("afp.sinks.github.subprocess.run", return_value=fake) as run:
        ref = sink.submit({
            "report_id": "afp_x", "subject_uri": "pkg:npm/eslint@9.2.0",
            "friction_type": "bug", "severity": "blocked", "goal": "g",
            "expectation": "e", "observed": "o",
        })
    assert ref == "https://github.com/user/repo/issues/42"
    args = run.call_args.args[0]
    assert args[:3] == ["gh", "issue", "create"]
    assert "--repo" in args and "user/repo" in args
    assert "--label" in args and "afp-report" in args


def test_github_sink_uses_human_readable_title_and_body():
    sink = GitHubIssuesSink(repo="user/repo", label="afp-report")
    report = {
        "report_id": "afp_x",
        "subject_uri": "pkg:github/Vasallo94/afp-protocol@0.2.0",
        "friction_type": "missing_capability",
        "fault_domain": "tool",
        "severity": "degraded",
        "goal": "Review local AFP drafts",
        "expectation": "AFP lists drafts for review",
        "observed": "Maintainer used jq manually",
        "workaround": "Use jq over .afp/drafts",
    }

    title = sink._title(report)
    body = sink._body(report)

    assert title == "[AFP/degraded] Review local AFP drafts"
    assert "## AFP Field Report" in body
    assert "- Subject: `pkg:github/Vasallo94/afp-protocol@0.2.0`" in body
    assert "- Type: `missing_capability`" in body
    assert "### Expected" in body
    assert "AFP lists drafts for review" in body
    assert "<details>" in body
    assert '"report_id": "afp_x"' in body


def test_github_sink_raises_on_failure():
    sink = GitHubIssuesSink(repo="user/repo", label="afp-report")
    fake = subprocess.CompletedProcess(args=["gh"], returncode=1, stdout="", stderr="boom")
    with patch("afp.sinks.github.subprocess.run", return_value=fake):
        with pytest.raises(RuntimeError):
            sink.submit({"report_id": "afp_x", "goal": "g"})
