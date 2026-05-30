import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import jsonschema

_SCHEMA_PATH = Path(__file__).parent / "schema" / "afp_manifest.schema.json"


class ManifestInvalid(Exception):
    """El afp.json no cumple su JSON Schema."""


@lru_cache(maxsize=1)
def _schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())


@dataclass
class Manifest:
    afp_version: str
    subject_uri: str
    sink: dict
    redaction: str = "required"
    accepts_remote: bool = False
    schema_extensions: list | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Manifest":
        try:
            jsonschema.validate(data, _schema())
        except jsonschema.ValidationError as exc:
            raise ManifestInvalid(exc.message) from exc
        return cls(
            afp_version=data["afp_version"],
            subject_uri=data["subject_uri"],
            sink=data["sink"],
            redaction=data.get("redaction", "required"),
            accepts_remote=data.get("accepts_remote", False),
            schema_extensions=data.get("schema_extensions"),
        )


def load_manifest(path: Path) -> Manifest:
    return Manifest.from_dict(json.loads(Path(path).read_text()))
