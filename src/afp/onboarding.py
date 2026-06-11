from __future__ import annotations

import json
from pathlib import Path

from afp.manifest import ManifestInvalid, load_manifest


class OnboardingError(ValueError):
    """Raised when an onboarding command cannot complete safely."""


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
