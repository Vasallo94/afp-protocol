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


def test_invalid_timestamp_fails():
    bad = _report_dict()
    bad["timestamp"] = "not-a-date"
    with pytest.raises(ReportInvalid):
        validate_report(bad)
