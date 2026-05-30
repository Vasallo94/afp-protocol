import json
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path(__file__).parents[1] / "src" / "afp" / "schema" / "field_report.schema.json"
VECTORS = Path(__file__).parent / "vectors"


def _schema():
    return json.loads(SCHEMA_PATH.read_text())


def test_schema_is_valid_jsonschema():
    jsonschema.Draft202012Validator.check_schema(_schema())


def test_valid_minimal_vector_passes():
    report = json.loads((VECTORS / "valid_minimal.json").read_text())
    jsonschema.validate(report, _schema())


def test_invalid_vector_fails():
    report = json.loads((VECTORS / "invalid_missing_required.json").read_text())
    with __import__("pytest").raises(jsonschema.ValidationError):
        jsonschema.validate(report, _schema())
