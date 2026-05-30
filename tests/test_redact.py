import pytest

from afp.redact import contains_secret, scan_for_secrets, SecretDetected, assert_no_secrets


@pytest.mark.parametrize("text", [
    "sk-ABCDEFGHIJKLMNOPQRSTUVWX",
    "ghp_0123456789abcdefghijklmnopqrstuvwxyz",
    "AKIAIOSFODNN7EXAMPLE",
    "-----BEGIN PRIVATE KEY-----",
])
def test_contains_secret_true(text):
    assert contains_secret(text) is True


@pytest.mark.parametrize("text", ["hola mundo", "pkg:npm/eslint@9.2.0", ""])
def test_contains_secret_false(text):
    assert contains_secret(text) is False


def test_scan_reports_offending_fields():
    report = {"goal": "usar token ghp_0123456789abcdefghijklmnopqrstuvwxyz", "observed": "ok"}
    assert scan_for_secrets(report) == ["goal"]


def test_assert_no_secrets_raises():
    report = {"observed": "AKIAIOSFODNN7EXAMPLE"}
    with pytest.raises(SecretDetected):
        assert_no_secrets(report)
