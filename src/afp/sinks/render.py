"""Renderizado compartido de un field report a issue (título + cuerpo markdown).

Único punto de verdad para la plantilla de issue de los sinks remotos
(`github_issues`, `gitlab_issues`). Centralizar aquí evita la triplicación
previa y deja un solo sitio donde aplicar el saneo de campos no confiables.
"""
import json

_TITLE_MAX_GOAL = 80


def render_title(report: dict) -> str:
    severity = report.get("severity", "unknown")
    goal = str(report.get("goal") or report.get("subject_uri") or "Field report")
    goal = " ".join(goal.split())
    if len(goal) > _TITLE_MAX_GOAL:
        goal = goal[: _TITLE_MAX_GOAL - 3].rstrip() + "..."
    return f"[AFP/{severity}] {goal}"


def render_body(report: dict) -> str:
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
    return "\n".join(sections)
