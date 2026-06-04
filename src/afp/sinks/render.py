"""Renderizado compartido de un field report a issue (título + cuerpo markdown).

Único punto de verdad para la plantilla de issue de los sinks remotos
(`github_issues`, `gitlab_issues`). Centralizar aquí evita la triplicación
previa y deja un solo sitio donde aplicar el saneo de campos no confiables.

Seguridad (§8 threat model — "spam"/"prompt injection vía reporte"): el
contenido de un field report es **dato no confiable**. Antes de incrustarlo en
un issue se neutraliza para que no pueda:
  - generar menciones/back-references (`@org`, `#123`) → notificaciones a terceros;
  - inyectar HTML (`</details>`, `<script>`) ni romper la estructura del cuerpo;
  - escapar de bloques de código (runs de backticks).
El JSON crudo se cerca con un fence dinámico más largo que cualquier run de
backticks presente, para que no pueda producirse un breakout del bloque.
"""
import json
import re

_TITLE_MAX_GOAL = 80
_ZWSP = "​"  # zero-width space: rompe autolinks/fences sin alterar lo legible


def sanitize_inline(text: object) -> str:
    """Neutraliza texto no confiable para incrustarlo como markdown de issue."""
    s = str(text)
    # 1) HTML: mata </details>, <script>, etc. (& primero para no doble-escapar).
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # 2) Autolinks de GitHub/GitLab: @mención y #ref dejan de enlazar/notificar.
    s = s.replace("@", "@" + _ZWSP).replace("#", "#" + _ZWSP)
    # 3) Code fences: romper runs de backticks impide abrir/cerrar bloques.
    s = s.replace("`", "`" + _ZWSP)
    return s


def _json_fence(payload: str) -> str:
    """Fence de backticks más largo que cualquier run presente (mín. 3)."""
    longest = max((len(run) for run in re.findall(r"`+", payload)), default=0)
    return "`" * max(3, longest + 1)


def render_title(report: dict) -> str:
    severity = report.get("severity", "unknown")
    goal = str(report.get("goal") or report.get("subject_uri") or "Field report")
    goal = " ".join(goal.split())
    if len(goal) > _TITLE_MAX_GOAL:
        goal = goal[: _TITLE_MAX_GOAL - 3].rstrip() + "..."
    return f"[AFP/{severity}] {goal}"


def _code(value: object) -> str:
    """Valor entre backticks inline, sin backticks internos que rompan el span."""
    return str(value).replace("`", "")


def render_body(report: dict) -> str:
    # Metadata: subject/enums están validados, pero defendemos igual el span.
    subject = _code(report.get("subject_uri", "unknown"))
    friction_type = _code(report.get("friction_type", "unknown"))
    fault_domain = _code(report.get("fault_domain", "unknown"))
    severity = _code(report.get("severity", "unknown"))
    # Texto libre: dato NO confiable → saneo completo.
    goal = sanitize_inline(report.get("goal", ""))
    expectation = sanitize_inline(report.get("expectation", ""))
    observed = sanitize_inline(report.get("observed", ""))
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
        sections.append(f"- Plan step: {sanitize_inline(plan_step)}")
    sections.extend([
        "",
        "### Goal",
        "",
        goal,
        "",
        "### Expected",
        "",
        expectation,
        "",
        "### Observed",
        "",
        observed,
    ])
    if workaround:
        sections.extend(["", "### Workaround", "", sanitize_inline(workaround)])
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    fence = _json_fence(payload)
    sections.extend([
        "",
        "<details>",
        "<summary>Raw AFP JSON</summary>",
        "",
        f"{fence}json",
        payload,
        fence,
        "",
        "</details>",
    ])
    return "\n".join(sections)
