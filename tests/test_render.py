from afp.sinks.render import render_body, render_title


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
