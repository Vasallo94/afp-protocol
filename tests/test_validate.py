import pytest

from afp.enums import FaultDomain, FrictionType, Severity
from afp.models import FieldReport
from afp.validate import validate_report, ReportInvalid
from afp.redact import SecretDetected


def _report_dict(**extra):
    r = FieldReport.create(
        subject_uri="pkg:pypi/ruff",
        goal="lintear",
        expectation="salida JSON",
        observed="texto plano",
        friction_type=FrictionType.WRONG_OUTPUT,
        fault_domain=FaultDomain.TOOL,
        severity=Severity.DEGRADED,
        **extra,
    )
    return r.to_dict()


def test_valid_report_passes():
    validate_report(_report_dict())


def test_missing_required_fails():
    bad = _report_dict()
    del bad["goal"]
    with pytest.raises(ReportInvalid):
        validate_report(bad)


def test_bad_enum_fails():
    bad = _report_dict()
    bad["severity"] = "catastrophic"
    with pytest.raises(ReportInvalid):
        validate_report(bad)


def test_secret_in_report_blocks():
    bad = _report_dict(workaround="usé ghp_0123456789abcdefghijklmnopqrstuvwxyz")
    with pytest.raises(SecretDetected):
        validate_report(bad)


def test_invalid_subject_uri_fails():
    bad = _report_dict()
    bad["subject_uri"] = "not-a-uri"
    with pytest.raises(ReportInvalid):
        validate_report(bad)


def test_unknown_extension_field_is_accepted():
    # Forward-compat (ADR-0001 opción A): additionalProperties permitido.
    ok = _report_dict()
    ok["experimental_signal"] = {"score": 0.9}
    validate_report(ok)


def test_newer_minor_schema_version_is_accepted():
    # Tolerancia por minor dentro del mismo major (ADR-0001).
    ok = _report_dict()
    ok["schema_version"] = "afp/0.99"
    validate_report(ok)


def test_different_major_schema_version_fails():
    bad = _report_dict()
    bad["schema_version"] = "afp/1.0"
    with pytest.raises(ReportInvalid):
        validate_report(bad)


def test_invalid_timestamp_fails():
    bad = _report_dict()
    bad["timestamp"] = "not-a-date"
    with pytest.raises(ReportInvalid):
        validate_report(bad)
