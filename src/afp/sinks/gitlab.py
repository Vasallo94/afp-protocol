import os
import subprocess

from afp.sinks.base import Sink
from afp.sinks.render import render_body, render_title


class GitLabIssuesSink(Sink):
    name = "gitlab_issues"

    def __init__(self, repo: str, label: str = "afp-report", host: str | None = None):
        self.repo = repo
        self.label = label
        self.host = host

    def _title(self, report: dict) -> str:
        return render_title(report)

    def _body(self, report: dict) -> str:
        return render_body(report)

    def submit(self, report: dict) -> str:
        cmd = [
            "glab", "issue", "create",
            "--repo", self.repo,
            "--title", self._title(report),
            "--description", self._body(report),
            "--label", self.label,
            "--yes",
        ]
        env = {**os.environ, "GITLAB_HOST": self.host} if self.host else None
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, env=env
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("glab issue create excedió el timeout") from exc
        if result.returncode != 0:
            raise RuntimeError(f"glab issue create falló: {result.stderr.strip()}")
        return result.stdout.strip()
