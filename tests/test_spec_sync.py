"""La spec (spec/schemas) es la fuente canónica; src/afp/schema (wheel Python)
y ts/schemas (paquete npm) son copias vendorizadas. Este test impide que
diverjan."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
CANONICAL = ROOT / "spec" / "schemas"
VENDORED_DIRS = [ROOT / "src" / "afp" / "schema", ROOT / "ts" / "schemas"]
SCHEMA_NAMES = ["field_report.schema.json", "afp_manifest.schema.json"]


@pytest.mark.parametrize("vendored_dir", VENDORED_DIRS, ids=lambda p: str(p.relative_to(ROOT)))
@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_vendored_schema_matches_canonical(vendored_dir, name):
    canonical = json.loads((CANONICAL / name).read_text(encoding="utf-8"))
    vendored = json.loads((vendored_dir / name).read_text(encoding="utf-8"))
    assert vendored == canonical, (
        f"{name} divergió: edita spec/schemas/{name} (canónico) y copia a {vendored_dir}/"
    )
