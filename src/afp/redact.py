"""Detección de secretos y PII de la clase "prohibido" (§5 del spec).

Cubre: secretos de alta confianza (tokens API, claves, JWT, Bearer) y emails
(PII directa). LIMITACIÓN (Fase 1a): NO cubre exhaustivamente otra PII como
teléfonos, nombres o direcciones. El agente que genera el reporte sigue siendo
responsable de la minimización de datos (§5.3); este filtro es una última red
de seguridad, no una garantía total.
"""
import re

# Patrones de la clase "prohibido" (§5 del spec). Lista mínima y ampliable.
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),                 # OpenAI-style
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),                # GitHub PAT
    re.compile(r"AKIA[0-9A-Z]{16}"),                    # AWS access key id
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),  # PEM
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),        # Slack tokens
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{6,}"),  # JWT
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}"),                            # Bearer token
    re.compile(r"(?i)(api[_-]?key|secret|password|access[_-]?key|token)\s*[:=]\s*['\"]?[A-Za-z0-9/_\-]{8,}"),  # key=value secret
    re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),  # email (PII directa)
]


class SecretDetected(Exception):
    """Se detectó un secreto en un reporte; el envío debe abortarse."""


def contains_secret(text: str) -> bool:
    if not isinstance(text, str):
        return False
    return any(p.search(text) for p in _SECRET_PATTERNS)


def _walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _walk_strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _walk_strings(v)


def scan_for_secrets(report: dict) -> list[str]:
    """Devuelve la lista de campos de primer nivel que contienen secretos."""
    offending = []
    for key, value in report.items():
        if any(contains_secret(s) for s in _walk_strings(value)):
            offending.append(key)
    return offending


def assert_no_secrets(report: dict) -> None:
    offending = scan_for_secrets(report)
    if offending:
        raise SecretDetected(f"secretos detectados en campos: {offending}")
