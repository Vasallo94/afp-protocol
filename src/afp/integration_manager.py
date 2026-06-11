from __future__ import annotations

import shutil
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path


class IntegrationError(ValueError):
    """Raised when an integration install request is invalid."""


@dataclass(frozen=True)
class Integration:
    name: str
    scope: str
    resource_parts: tuple[str, ...]
    relative_destination: tuple[str, ...] | None


INTEGRATIONS: dict[str, Integration] = {
    "codex": Integration(
        name="codex",
        scope="global",
        resource_parts=("integrations", "codex", "afp-report"),
        relative_destination=(".codex", "skills", "afp-report"),
    ),
    "claude-code": Integration(
        name="claude-code",
        scope="global",
        resource_parts=("integrations", "claude-code", "afp-report"),
        relative_destination=(".claude", "skills", "afp-report"),
    ),
    "cursor": Integration(
        name="cursor",
        scope="project",
        resource_parts=("integrations", "cursor", "afp-report.mdc"),
        relative_destination=(".cursor", "rules", "afp-report.mdc"),
    ),
    "generic": Integration(
        name="generic",
        scope="prompt",
        resource_parts=("integrations", "generic", "AFP-INSTRUCTIONS.md"),
        relative_destination=None,
    ),
}


def destination_for(name: str, *, home: Path, project: Path | None) -> Path | None:
    integration = _get(name)
    if integration.relative_destination is None:
        return None
    base = home if integration.scope == "global" else project
    if base is None:
        raise IntegrationError(f"{name} requires --project PATH")
    return base.joinpath(*integration.relative_destination)


def status_for(name: str, *, home: Path, project: Path | None) -> str:
    integration = _get(name)
    if integration.scope == "project" and project is None:
        return "missing"
    destination = destination_for(name, home=home, project=project)
    if destination is None:
        return "available"
    return "installed" if destination.exists() or destination.is_symlink() else "missing"


def install_integration(
    name: str,
    *,
    home: Path,
    project: Path | None,
    global_: bool,
    out: Path | None,
    force: bool,
    mode: str = "copy",
) -> Path:
    integration = _get(name)
    if integration.scope == "global" and not global_:
        raise IntegrationError(f"{name} requires --global")
    if integration.scope == "project" and project is None:
        raise IntegrationError(f"{name} requires --project PATH")
    if mode not in {"copy", "symlink"}:
        raise IntegrationError("--mode must be copy or symlink")

    source = _resource_path(integration)
    if integration.scope == "prompt":
        if out is None:
            raise IntegrationError("generic requires --out PATH")
        _replace(source, out, force=force, mode=mode)
        return out

    destination = destination_for(name, home=home, project=project)
    assert destination is not None
    _replace(source, destination, force=force, mode=mode)
    return destination


def _resource_path(integration: Integration) -> Path:
    resource = files("afp")
    for part in integration.resource_parts:
        resource = resource.joinpath(part)
    return Path(str(resource))


def _replace(source: Path, destination: Path, *, force: bool, mode: str) -> None:
    if destination.exists() or destination.is_symlink():
        if _same_content(source, destination):
            return
        if not force:
            raise IntegrationError(f"destination already exists: {destination}")
        backup = destination.with_name(destination.name + ".bak")
        _remove_existing(backup)
        destination.rename(backup)

    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "symlink":
        destination.symlink_to(source, target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def _same_content(source: Path, destination: Path) -> bool:
    if source.is_file() and destination.is_file():
        return source.read_bytes() == destination.read_bytes()
    if source.is_dir() and destination.is_dir():
        source_files = sorted(path.relative_to(source) for path in source.rglob("*") if path.is_file())
        destination_files = sorted(
            path.relative_to(destination) for path in destination.rglob("*") if path.is_file()
        )
        if source_files != destination_files:
            return False
        return all(
            (source / rel).read_bytes() == (destination / rel).read_bytes()
            for rel in source_files
        )
    return False


def _remove_existing(path: Path) -> None:
    if not (path.exists() or path.is_symlink()):
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def _get(name: str) -> Integration:
    try:
        return INTEGRATIONS[name]
    except KeyError as exc:
        raise IntegrationError(f"unknown integration: {name}") from exc
