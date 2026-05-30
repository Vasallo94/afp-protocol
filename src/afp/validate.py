import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import jsonschema

from afp.identity import validate_subject_uri, InvalidSubjectUri
from afp.redact import assert_no_secrets

_SCHEMA_PATH = Path(__file__).parent / "schema" / "field_report.schema.json"


class ReportInvalid(Exception):
    """El reporte no cumple el JSON Schema de AFP."""


@lru_cache(maxsize=1)
def load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())


_format_checker = jsonschema.FormatChecker()


@_format_checker.checks("date-time", raises=ValueError)
def _check_date_time(value: object) -> bool:
    if not isinstance(value, str):
        return True
    datetime.fromisoformat(value)  # raises ValueError on bad input
    return True


def validate_report(report: dict) -> None:
    """Valida contra el JSON Schema y bloquea si hay secretos.

    Orden: primero el hard-block de secretos (§5), luego el schema,
    luego validación semántica del subject_uri.
    """
    assert_no_secrets(report)
    try:
        jsonschema.validate(report, load_schema(), format_checker=_format_checker)
    except jsonschema.ValidationError as exc:
        raise ReportInvalid(exc.message) from exc
    try:
        validate_subject_uri(report["subject_uri"])
    except InvalidSubjectUri as exc:
        raise ReportInvalid(f"subject_uri inválido: {exc}") from exc
