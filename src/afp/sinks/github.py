import subprocess

from afp.sinks.base import Sink
from afp.sinks.render import render_body, render_title


class GitHubIssuesSink(Sink):
    name = "github_issues"

    def __init__(self, repo: str, label: str = "afp-report"):
        self.repo = repo
        self.label = label

    def _title(self, report: dict) -> str:
        return render_title(report)

    def _body(self, report: dict) -> str:
        return render_body(report)

    def submit(self, report: dict) -> str:
        cmd = [
            "gh", "issue", "create",
            "--repo", self.repo,
            "--label", self.label,
            "--title", self._title(report),
            "--body", self._body(report),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("gh issue create excedió el timeout") from exc
        if result.returncode != 0:
            raise RuntimeError(f"gh issue create falló: {result.stderr.strip()}")
        return result.stdout.strip()
