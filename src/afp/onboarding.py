from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from afp import __version__
from afp.integration_manager import status_for
from afp.manifest import ManifestInvalid, load_manifest


class OnboardingError(ValueError):
    """Raised when an onboarding command cannot complete safely."""


@dataclass(frozen=True)
class DoctorCheck:
    status: str
    name: str
    detail: str


def build_manifest(
    *,
    subject: str,
    sink: str,
    repo: str | None,
    host: str | None,
    label: str,
) -> dict:
    sink_payload: dict[str, str] = {"type": sink}
    if sink == "github_issues":
        if not repo:
            raise OnboardingError("--repo is required for github_issues")
        sink_payload["repo"] = repo
    elif sink == "gitlab_issues":
        if not repo:
            raise OnboardingError("--repo is required for gitlab_issues")
        if host:
            sink_payload["host"] = host
        sink_payload["repo"] = repo
    else:
        raise OnboardingError("--sink must be github_issues or gitlab_issues")
    sink_payload["label"] = label
    return {
        "afp_version": "0.2",
        "subject_uri": subject,
        "sink": sink_payload,
        "redaction": "required",
        "accepts_remote": True,
        "schema_extensions": [],
    }


def write_manifest(
    *,
    dir_: Path,
    manifest: dict,
    force: bool,
) -> Path:
    target = Path(dir_) / "afp.json"
    if target.exists() and not force:
        raise OnboardingError(f"afp.json already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        load_manifest(target)
    except (ManifestInvalid, OSError, json.JSONDecodeError) as exc:
        raise OnboardingError(f"generated manifest is invalid: {exc}") from exc
    return target


def doctor_checks(*, dir_: Path, home: Path) -> list[DoctorCheck]:
    checks = [DoctorCheck("OK", "CLI", f"afp {__version__}")]
    base = Path(dir_)
    manifest_path = base / "afp.json"

    if manifest_path.exists():
        try:
            load_manifest(manifest_path)
        except (ManifestInvalid, OSError, json.JSONDecodeError) as exc:
            checks.append(DoctorCheck("FAIL", "manifest", str(exc)))
        else:
            checks.append(DoctorCheck("OK", "manifest", str(manifest_path)))
    else:
        checks.append(DoctorCheck("MISSING", "manifest", "run afp init"))

    for name in ("codex", "claude-code"):
        status = status_for(name, home=home, project=base)
        if status == "installed":
            checks.append(DoctorCheck("OK", f"{name} skill", "installed"))
        else:
            checks.append(
                DoctorCheck(
                    "MISSING",
                    f"{name} skill",
                    f"run afp integrations install {name} --global",
                )
            )

    drafts = list((base / ".afp" / "drafts").glob("*.json"))
    if drafts:
        checks.append(
            DoctorCheck(
                "WARN",
                "drafts",
                f"{len(drafts)} pending, review with afp drafts list --dir {base}",
            )
        )
    else:
        checks.append(DoctorCheck("OK", "drafts", "none pending"))

    return checks
