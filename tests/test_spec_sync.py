"""La spec (spec/schemas) es la fuente canónica; src/afp/schema es la copia
vendorizada que viaja en el wheel. Este test impide que diverjan."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
CANONICAL = ROOT / "spec" / "schemas"
VENDORED = ROOT / "src" / "afp" / "schema"


@pytest.mark.parametrize(
    "name", ["field_report.schema.json", "afp_manifest.schema.json"]
)
def test_vendored_schema_matches_canonical(name):
    canonical = json.loads((CANONICAL / name).read_text(encoding="utf-8"))
    vendored = json.loads((VENDORED / name).read_text(encoding="utf-8"))
    assert vendored == canonical, (
        f"{name} divergió: edita spec/schemas/{name} (canónico) y copia a src/afp/schema/"
    )
