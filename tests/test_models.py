import pytest

from afp.enums import FaultDomain, FrictionType, Severity
from afp.models import FieldReport


def _kwargs():
    return dict(
        subject_uri="pkg:pypi/ruff",
        goal="lintear el proyecto",
        expectation="salida JSON con la lista de errores",
        observed="salida en texto plano sin estructura",
        friction_type=FrictionType.WRONG_OUTPUT,
        fault_domain=FaultDomain.TOOL,
        severity=Severity.DEGRADED,
    )


def test_create_fills_generated_fields():
    r = FieldReport.create(**_kwargs())
    assert r.report_id.startswith("afp_")
    assert r.schema_version == "afp/0.2"
    assert r.timestamp.endswith("+00:00")


def test_to_dict_drops_none_and_serializes_enums():
    r = FieldReport.create(**_kwargs())
    d = r.to_dict()
    assert d["friction_type"] == "wrong_output"
    assert d["fault_domain"] == "tool"
    assert "workaround" not in d


def test_round_trip_from_dict():
    r = FieldReport.create(**_kwargs(), workaround="parsear a mano")
    d = r.to_dict()
    r2 = FieldReport.from_dict(d)
    assert r2.to_dict() == d
    assert r2.workaround == "parsear a mano"


def test_from_dict_rejects_invalid_subject_uri():
    from afp.identity import InvalidSubjectUri
    d = FieldReport.create(**_kwargs()).to_dict()
    d["subject_uri"] = "not-a-uri"
    with pytest.raises(InvalidSubjectUri):
        FieldReport.from_dict(d)
