from afp.enums import FrictionType, FaultDomain, Severity, Confidence, Reproducibility


def test_friction_type_values():
    assert {e.value for e in FrictionType} == {
        "bug", "undocumented_behavior", "missing_capability",
        "confusing_interface", "wrong_output", "integration_mismatch",
    }


def test_fault_domain_values():
    assert {e.value for e in FaultDomain} == {
        "tool", "agent_misuse", "ambiguous_contract", "environment_issue",
        "permission_denied", "rate_limit", "timeout",
    }


def test_severity_values():
    assert {e.value for e in Severity} == {"blocked", "degraded", "cosmetic"}


def test_enums_are_str():
    assert FrictionType.BUG == "bug"
    assert Severity.BLOCKED.value == "blocked"
    assert Confidence.HIGH == "high"
    assert Reproducibility.ONCE == "once"
