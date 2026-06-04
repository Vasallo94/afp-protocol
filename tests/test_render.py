import json
import re

from afp.sinks.render import render_body, render_title, sanitize_inline


def _report():
    return {
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


def test_render_title_uses_severity_and_goal():
    assert render_title(_report()) == "[AFP/degraded] Review local AFP drafts"


def test_render_title_falls_back_to_subject_then_default():
    assert render_title({"severity": "blocked", "subject_uri": "pkg:npm/x"}) == (
        "[AFP/blocked] pkg:npm/x"
    )
    assert render_title({}) == "[AFP/unknown] Field report"


def test_render_title_truncates_long_goal():
    long_goal = "x" * 200
    title = render_title({"severity": "degraded", "goal": long_goal})
    assert title.endswith("...")
    assert len(title) <= len("[AFP/degraded] ") + 80


ZWSP = "​"


def test_sanitize_neutralizes_mentions():
    out = sanitize_inline("ping @org/team please")
    assert "@org/team" not in out
    assert "@" + ZWSP in out


def test_sanitize_neutralizes_issue_refs():
    out = sanitize_inline("regresión como en #123")
    assert "#123" not in out
    assert "#" + ZWSP in out


def test_sanitize_escapes_html_so_details_cannot_close():
    out = sanitize_inline("</details><script>alert(1)</script>")
    assert "</details>" not in out
    assert "<script>" not in out
    assert "&lt;/details&gt;" in out


def test_sanitize_breaks_code_fence_runs():
    out = sanitize_inline("```python\nmalicious\n```")
    assert "```" not in out


def test_render_body_sanitizes_free_text_fields():
    report = {"severity": "blocked", "observed": "rompe con ``` y @org y #1"}
    body = render_body(report)
    # En la sección de prosa el contenido va neutralizado.
    observed_section = body.split("### Observed", 1)[1].split("<details>", 1)[0]
    assert "```" not in observed_section
    assert "@org" not in observed_section
    assert "#1" not in observed_section


def test_render_body_json_block_survives_backtick_payload():
    report = {
        "report_id": "afp_x",
        "severity": "blocked",
        "observed": "intento de fuga: ``` cierre falso ``` y ````",
    }
    body = render_body(report)
    # Localiza el bloque ```json … ``` (fence dinámico de >=3 backticks) y
    # confirma que el JSON crudo es íntegro (no hubo breakout).
    m = re.search(r"(?m)^(`{3,})json\n(.*?)\n\1$", body, re.DOTALL)
    assert m, "no se encontró un bloque json bien cercado"
    fence = m.group(1)
    assert len(fence) >= 5  # mayor que el run de 4 backticks del payload
    assert json.loads(m.group(2)) == report


def test_render_body_has_sections_and_raw_json():
    body = render_body(_report())
    assert "## AFP Field Report" in body
    assert "- Subject: `pkg:github/Vasallo94/afp-protocol@0.2.0`" in body
    assert "- Type: `missing_capability`" in body
    assert "### Expected" in body
    assert "AFP lists drafts for review" in body
    assert "### Workaround" in body
    assert "<details>" in body
    assert '"report_id": "afp_x"' in body
