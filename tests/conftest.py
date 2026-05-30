import pytest

from afp.enums import FaultDomain, FrictionType, Severity
from afp.models import FieldReport


@pytest.fixture
def minimal_report() -> dict:
    return FieldReport.create(
        subject_uri="pkg:pypi/ruff",
        goal="lintear el proyecto",
        expectation="salida JSON con errores",
        observed="texto plano",
        friction_type=FrictionType.WRONG_OUTPUT,
        fault_domain=FaultDomain.TOOL,
        severity=Severity.DEGRADED,
    ).to_dict()
