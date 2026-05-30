import json
import subprocess

from afp.sinks.base import Sink


class GitHubIssuesSink(Sink):
    name = "github_issues"

    def __init__(self, repo: str, label: str = "afp-report"):
        self.repo = repo
        self.label = label

    def _title(self, report: dict) -> str:
        severity = report.get("severity", "unknown")
        goal = str(report.get("goal") or report.get("subject_uri") or "Field report")
        goal = " ".join(goal.split())
        if len(goal) > 80:
            goal = goal[:77].rstrip() + "..."
        return f"[AFP/{severity}] {goal}"

    def _body(self, report: dict) -> str:
        subject = report.get("subject_uri", "unknown")
        friction_type = report.get("friction_type", "unknown")
        fault_domain = report.get("fault_domain", "unknown")
        severity = report.get("severity", "unknown")
        goal = report.get("goal", "")
        expectation = report.get("expectation", "")
        observed = report.get("observed", "")
        workaround = report.get("workaround")
        plan_step = report.get("plan_step")

        sections = [
            "## AFP Field Report",
            "",
            f"- Subject: `{subject}`",
            f"- Type: `{friction_type}`",
            f"- Fault domain: `{fault_domain}`",
            f"- Severity: `{severity}`",
        ]
        if plan_step:
            sections.append(f"- Plan step: {plan_step}")
        sections.extend([
            "",
            "### Goal",
            "",
            str(goal),
            "",
            "### Expected",
            "",
            str(expectation),
            "",
            "### Observed",
            "",
            str(observed),
        ])
        if workaround:
            sections.extend(["", "### Workaround", "", str(workaround)])
        sections.extend([
            "",
            "<details>",
            "<summary>Raw AFP JSON</summary>",
            "",
            "```json",
            json.dumps(report, ensure_ascii=False, indent=2),
            "```",
            "",
            "</details>",
        ])
        return (
            "\n".join(sections)
        )

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
