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


@pytest.mark.parametrize("text", [
    "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dQw4w9WgXcQabcd",  # JWT
    "Authorization: Bearer abcdefghijklmnopqrstuvwx1234",                 # Bearer
    "api_key=ABCD1234EFGH5678",                                          # key=value
    "password: hunter2supersecret",                                      # key=value
])
def test_contains_secret_true_extended(text):
    assert contains_secret(text) is True


@pytest.mark.parametrize("text", [
    "el token expira mañana",          # 'token' sin separador := ni valor
    "password reset link en el email", # 'password' seguido de palabra, no de valor
    "necesito tu api para integrarlo", # no hay keyword de secreto completa
])
def test_contains_secret_false_near_miss(text):
    assert contains_secret(text) is False


def test_email_is_detected_as_pii():
    assert contains_secret("escribe a juan.perez@example.com por favor") is True


def test_package_with_at_is_not_email():
    # un PURL con @version no debe confundirse con un email
    assert contains_secret("pkg:npm/eslint@9.2.0") is False
