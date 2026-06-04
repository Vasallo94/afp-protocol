import pytest

from afp.redact import (
    contains_secret, scan_for_secrets, SecretDetected, assert_no_secrets, redact_pii,
)


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


def test_email_is_not_a_hard_secret():
    # Cambio de comportamiento (#10): un email mencionado NO aborta el envío;
    # se redacta y el reporte continúa.
    assert contains_secret("escribe a juan.perez@example.com por favor") is False


def test_assert_no_secrets_does_not_block_on_email():
    assert_no_secrets({"observed": "el error mostraba soporte@empresa.com"})


def test_redact_pii_replaces_email_and_keeps_rest():
    out = redact_pii({"observed": "escribe a juan.perez@example.com hoy"})
    assert "juan.perez@example.com" not in out["observed"]
    assert "[REDACTED_EMAIL]" in out["observed"]
    assert out["observed"].startswith("escribe a ")


def test_redact_pii_walks_nested_structures():
    out = redact_pii({"evidence": [{"line": "ping a@b.com"}]})
    assert out["evidence"][0]["line"] == "ping [REDACTED_EMAIL]"


def test_redact_pii_leaves_tokens_untouched():
    # redact_pii solo trata PII (email); los secretos los corta assert_no_secrets.
    secret = "ghp_0123456789abcdefghijklmnopqrstuvwxyz"
    out = redact_pii({"workaround": secret})
    assert out["workaround"] == secret


def test_package_with_at_is_not_email():
    # un PURL con @version no debe confundirse con un email
    assert contains_secret("pkg:npm/eslint@9.2.0") is False
