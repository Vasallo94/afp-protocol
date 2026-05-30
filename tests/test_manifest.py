import json

import pytest

from afp.manifest import Manifest, load_manifest, ManifestInvalid


def _good():
    return {
        "afp_version": "0.2",
        "subject_uri": "mcp://github.com/user/nadir-astro",
        "sink": {"type": "github_issues", "repo": "user/nadir-astro", "label": "afp-report"},
        "redaction": "required",
        "accepts_remote": True,
    }


def test_load_manifest_ok(tmp_path):
    p = tmp_path / "afp.json"
    p.write_text(json.dumps(_good()))
    m = load_manifest(p)
    assert isinstance(m, Manifest)
    assert m.sink["type"] == "github_issues"
    assert m.accepts_remote is True


def test_manifest_defaults(tmp_path):
    data = _good()
    del data["accepts_remote"]
    del data["redaction"]
    p = tmp_path / "afp.json"
    p.write_text(json.dumps(data))
    m = load_manifest(p)
    assert m.redaction == "required"
    assert m.accepts_remote is False


def test_manifest_missing_sink_fails(tmp_path):
    data = _good()
    del data["sink"]
    p = tmp_path / "afp.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ManifestInvalid):
        load_manifest(p)
