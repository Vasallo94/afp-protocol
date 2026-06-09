"""Ejecuta los test vectors agnósticos de lenguaje (spec/vectors/) contra esta
implementación. Cualquier implementación AFP conforme debe pasar estos mismos
vectores; este runner es el de la implementación de referencia."""
import copy
import json
from pathlib import Path

import pytest

from afp.manifest import Manifest, ManifestInvalid
from afp.redact import SecretDetected, redact_pii, scan_for_secrets
from afp.sinks import subject_is_owned_by
from afp.validate import ReportInvalid, validate_report

VECTORS = Path(__file__).parents[1] / "spec" / "vectors"


def _cases(filename: str) -> list:
    data = json.loads((VECTORS / filename).read_text(encoding="utf-8"))
    return [pytest.param(case, id=case["description"]) for case in data]


@pytest.mark.parametrize("case", _cases("field_report.json"))
def test_field_report_vectors(case):
    report = copy.deepcopy(case["data"])
    if case["valid"]:
        validate_report(report)
    else:
        with pytest.raises((ReportInvalid, SecretDetected)):
            validate_report(report)


@pytest.mark.parametrize("case", _cases("manifest.json"))
def test_manifest_vectors(case):
    if case["valid"]:
        Manifest.from_dict(case["data"])
    else:
        with pytest.raises(ManifestInvalid):
            Manifest.from_dict(case["data"])


@pytest.mark.parametrize("case", _cases("ownership.json"))
def test_ownership_vectors(case):
    assert (
        subject_is_owned_by(case["report_subject"], case["manifest_subject"])
        is case["owned"]
    )


@pytest.mark.parametrize("case", _cases("redaction.json"))
def test_redaction_vectors(case):
    if case["outcome"] == "secret_block":
        assert sorted(scan_for_secrets(case["data"])) == sorted(case["offending_fields"])
    else:
        assert scan_for_secrets(case["data"]) == []
        assert redact_pii(case["data"]) == case["expected"]
