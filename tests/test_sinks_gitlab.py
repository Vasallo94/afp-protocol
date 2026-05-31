from unittest.mock import patch
import subprocess

import pytest

from afp.sinks.gitlab import GitLabIssuesSink


def _report():
    return {
        "report_id": "afp_x", "subject_uri": "mcp://gl.local/grp/mcp#tool",
        "friction_type": "bug", "severity": "blocked", "goal": "g",
        "expectation": "e", "observed": "o",
    }


def test_gitlab_sink_calls_glab_and_returns_url():
    sink = GitLabIssuesSink(repo="grp/proj", label="afp-report")
    fake = subprocess.CompletedProcess(
        args=["glab"], returncode=0,
        stdout="https://gl.local/grp/proj/-/issues/7\n", stderr="",
    )
    with patch("afp.sinks.gitlab.subprocess.run", return_value=fake) as run:
        ref = sink.submit(_report())
    assert ref == "https://gl.local/grp/proj/-/issues/7"
    args = run.call_args.args[0]
    assert args[:3] == ["glab", "issue", "create"]
    assert "--repo" in args and "grp/proj" in args
    assert "--label" in args and "afp-report" in args


def test_gitlab_sink_injects_host_env():
    sink = GitLabIssuesSink(repo="grp/proj", host="gl.local")
    fake = subprocess.CompletedProcess(args=["glab"], returncode=0, stdout="url", stderr="")
    with patch("afp.sinks.gitlab.subprocess.run", return_value=fake) as run:
        sink.submit(_report())
    env = run.call_args.kwargs["env"]
    assert env["GITLAB_HOST"] == "gl.local"


def test_gitlab_sink_no_host_passes_no_env():
    sink = GitLabIssuesSink(repo="grp/proj")
    fake = subprocess.CompletedProcess(args=["glab"], returncode=0, stdout="url", stderr="")
    with patch("afp.sinks.gitlab.subprocess.run", return_value=fake) as run:
        sink.submit(_report())
    assert run.call_args.kwargs.get("env") is None


def test_gitlab_sink_raises_on_failure():
    sink = GitLabIssuesSink(repo="grp/proj")
    fake = subprocess.CompletedProcess(args=["glab"], returncode=1, stdout="", stderr="boom")
    with patch("afp.sinks.gitlab.subprocess.run", return_value=fake):
        with pytest.raises(RuntimeError):
            sink.submit(_report())


def test_gitlab_sink_raises_on_timeout():
    sink = GitLabIssuesSink(repo="grp/proj")
    with patch("afp.sinks.gitlab.subprocess.run",
               side_effect=subprocess.TimeoutExpired(cmd=["glab"], timeout=30)):
        with pytest.raises(RuntimeError):
            sink.submit(_report())
