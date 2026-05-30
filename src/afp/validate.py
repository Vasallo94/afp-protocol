import json
from functools import lru_cache
from pathlib import Path

import jsonschema

from afp.redact import assert_no_secrets

_SCHEMA_PATH = Path(__file__).parent / "schema" / "field_report.schema.json"


class ReportInvalid(Exception):
    """El reporte no cumple el JSON Schema de AFP."""


@lru_cache(maxsize=1)
def load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())


def validate_report(report: dict) -> None:
    """Valida contra el JSON Schema y bloquea si hay secretos.

    Orden: primero el hard-block de secretos (§5), luego el schema.
    """
    assert_no_secrets(report)
    try:
        jsonschema.validate(report, load_schema())
    except jsonschema.ValidationError as exc:
        raise ReportInvalid(exc.message) from exc
