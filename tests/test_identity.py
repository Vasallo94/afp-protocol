import pytest

from afp.identity import validate_subject_uri, InvalidSubjectUri


@pytest.mark.parametrize("uri", [
    "pkg:npm/eslint@9.2.0",
    "pkg:pypi/ruff",
    "https://api.stripe.com/v1/charges",
    "mcp://github.com/user/nadir-astro#resolve_target",
    "afp:skill/superpowers/test-driven-development",
    "afp:bin/sha256:abc123",
])
def test_valid_subject_uris(uri):
    assert validate_subject_uri(uri) == uri


@pytest.mark.parametrize("uri", ["", "eslint", "ftp://x", "pkg:", "://nope"])
def test_invalid_subject_uris(uri):
    with pytest.raises(InvalidSubjectUri):
        validate_subject_uri(uri)


def test_purl_must_parse():
    with pytest.raises(InvalidSubjectUri):
        validate_subject_uri("pkg:")
