from dataclasses import dataclass
from pathlib import Path

from afp.manifest import Manifest, load_manifest

LOCAL_SINKS = ["local", "draft"]
_MANIFEST_LOCATIONS = ("afp.json", ".well-known/afp.json")


@dataclass
class RoutingDecision:
    has_manifest: bool
    manifest: Manifest | None
    allowed_sinks: list[str]


def _find_manifest(start_dir: Path) -> Path | None:
    for rel in _MANIFEST_LOCATIONS:
        candidate = start_dir / rel
        if candidate.is_file():
            return candidate
    return None


def discover(start_dir: Path) -> RoutingDecision:
    """Resuelve el buzón y la política de sinks para una tool.

    Regla dura (§4.2): sin manifiesto, NUNCA se permite un sink remoto;
    solo local/draft. Con manifiesto, los sinks remotos requieren
    accepts_remote=True.
    """
    start_dir = Path(start_dir)
    manifest_path = _find_manifest(start_dir)
    if manifest_path is None:
        return RoutingDecision(False, None, list(LOCAL_SINKS))

    manifest = load_manifest(manifest_path)
    allowed = list(LOCAL_SINKS)
    if manifest.accepts_remote and manifest.sink["type"] not in allowed:
        allowed.append(manifest.sink["type"])
    return RoutingDecision(True, manifest, allowed)
