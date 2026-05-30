# AFP Fase 1 — Implementación de referencia (Python) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir la librería + CLI de referencia de AFP en Python que permita a un agente generar un *field report* válido, redactarlo/minimizarlo, descubrir el buzón de la tool y depositarlo respetando la regla "sin manifiesto, nunca auto-envío".

**Architecture:** Núcleo como librería Python (`src/afp/`) con responsabilidades aisladas: enums → modelo → identidad (PURL) → redacción/secretos → validación (JSON Schema) → manifiesto → descubrimiento/routing → sinks (local, draft, github_issues). Una CLI fina (`typer`) orquesta el núcleo. TDD con `pytest`; commits frecuentes por tarea.

**Tech Stack:** Python ≥3.11, uv (gestor), `jsonschema` (validación), `packageurl-python` (PURL), `typer` (CLI), `gh` CLI (depósito a GitHub vía subprocess), `pytest` (tests).

**Spec de referencia:** `docs/superpowers/specs/2026-05-30-afp-protocol-design.md` (v0.2.1).

---

## File Structure

```
afp-protocol/
├── pyproject.toml                       # proyecto uv + deps + script `afp`
├── src/afp/
│   ├── __init__.py                      # versión + exports
│   ├── enums.py                         # FrictionType, FaultDomain, Severity, Confidence, Reproducibility
│   ├── identity.py                      # validación/normalización de subject_uri (PURL-based)
│   ├── models.py                        # FieldReport (dataclass) + to_dict/from_dict + create()
│   ├── redact.py                        # detección de secretos (clase "prohibido") + helpers
│   ├── validate.py                      # validación contra JSON Schema + hard-block de secretos
│   ├── manifest.py                      # Manifest (afp.json) parse/validate
│   ├── discovery.py                     # buscar afp.json + RoutingDecision (política de sinks)
│   ├── sinks/
│   │   ├── __init__.py                  # factoría get_sink + conjuntos LOCAL/REMOTE + route()
│   │   ├── base.py                      # clase base Sink
│   │   ├── local.py                     # LocalSink → .afp/reports.jsonl
│   │   ├── draft.py                     # DraftSink → .afp/drafts/<id>.json
│   │   └── github.py                    # GitHubIssuesSink → gh issue create
│   ├── cli.py                           # typer app: validate / report / submit
│   └── schema/
│       ├── field_report.schema.json     # JSON Schema del field report
│       └── afp_manifest.schema.json     # JSON Schema del afp.json
└── tests/
    ├── conftest.py                      # fixtures: report válido mínimo
    ├── vectors/
    │   ├── valid_minimal.json
    │   └── invalid_missing_required.json
    ├── test_enums.py
    ├── test_identity.py
    ├── test_models.py
    ├── test_redact.py
    ├── test_validate.py
    ├── test_manifest.py
    ├── test_discovery.py
    ├── test_sinks_local.py
    ├── test_sinks_draft.py
    ├── test_sinks_github.py
    ├── test_routing.py
    └── test_cli.py
```

**Fuera de este plan (follow-up):** sink `file` y `http`, inferencia completa de repo (Capa 2 más allá de "sin manifiesto = local/draft"), el Harvester, la Claude Code Skill, y la Fase 1.5 normativa (RFC 2119 / test vectors exhaustivos).

---

### Task 0: Scaffolding del proyecto

**Files:**
- Create: `pyproject.toml`
- Create: `src/afp/__init__.py`
- Create: `tests/__init__.py` (vacío)

- [ ] **Step 1: Crear `pyproject.toml`**

```toml
[project]
name = "afp"
version = "0.2.0"
description = "Agent Feedback Protocol — reference implementation"
requires-python = ">=3.11"
dependencies = [
    "jsonschema>=4.21",
    "packageurl-python>=0.15",
    "typer>=0.12",
]

[project.scripts]
afp = "afp.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/afp"]

[tool.hatch.build.targets.wheel.force-include]
"src/afp/schema" = "afp/schema"

[dependency-groups]
dev = ["pytest>=8"]
```

- [ ] **Step 2: Crear paquetes vacíos**

```bash
mkdir -p src/afp/sinks src/afp/schema tests/vectors
touch src/afp/__init__.py src/afp/sinks/__init__.py tests/__init__.py
```

- [ ] **Step 3: Escribir `src/afp/__init__.py`**

```python
"""AFP — Agent Feedback Protocol, reference implementation."""

__version__ = "0.2.0"
SCHEMA_VERSION = "afp/0.2"
```

- [ ] **Step 4: Instalar dependencias y verificar**

Run: `uv sync`
Expected: crea `.venv` e instala jsonschema, packageurl-python, typer, pytest sin error.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/afp/__init__.py src/afp/sinks/__init__.py tests/__init__.py
git commit -m "chore: scaffold afp python package with uv"
```

---

### Task 1: Enums del protocolo

**Files:**
- Create: `src/afp/enums.py`
- Test: `tests/test_enums.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_enums.py
from afp.enums import FrictionType, FaultDomain, Severity, Confidence, Reproducibility


def test_friction_type_values():
    assert {e.value for e in FrictionType} == {
        "bug", "undocumented_behavior", "missing_capability",
        "confusing_interface", "wrong_output", "integration_mismatch",
    }


def test_fault_domain_values():
    assert {e.value for e in FaultDomain} == {
        "tool", "agent_misuse", "ambiguous_contract", "environment_issue",
        "permission_denied", "rate_limit", "timeout",
    }


def test_severity_values():
    assert {e.value for e in Severity} == {"blocked", "degraded", "cosmetic"}


def test_enums_are_str():
    assert FrictionType.BUG == "bug"
    assert Severity.BLOCKED.value == "blocked"
    assert Confidence.HIGH == "high"
    assert Reproducibility.ONCE == "once"
```

- [ ] **Step 2: Ejecutar el test para verque falla**

Run: `uv run pytest tests/test_enums.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'afp.enums'`

- [ ] **Step 3: Escribir la implementación mínima**

```python
# src/afp/enums.py
from enum import Enum


class FrictionType(str, Enum):
    BUG = "bug"
    UNDOCUMENTED_BEHAVIOR = "undocumented_behavior"
    MISSING_CAPABILITY = "missing_capability"
    CONFUSING_INTERFACE = "confusing_interface"
    WRONG_OUTPUT = "wrong_output"
    INTEGRATION_MISMATCH = "integration_mismatch"


class FaultDomain(str, Enum):
    TOOL = "tool"
    AGENT_MISUSE = "agent_misuse"
    AMBIGUOUS_CONTRACT = "ambiguous_contract"
    ENVIRONMENT_ISSUE = "environment_issue"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"


class Severity(str, Enum):
    BLOCKED = "blocked"
    DEGRADED = "degraded"
    COSMETIC = "cosmetic"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Reproducibility(str, Enum):
    DETERMINISTIC = "deterministic"
    INTERMITTENT = "intermittent"
    ONCE = "once"
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `uv run pytest tests/test_enums.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/afp/enums.py tests/test_enums.py
git commit -m "feat: add AFP protocol enums (friction_type, fault_domain, severity)"
```

---

### Task 2: JSON Schema del field report

**Files:**
- Create: `src/afp/schema/field_report.schema.json`
- Create: `tests/vectors/valid_minimal.json`
- Create: `tests/vectors/invalid_missing_required.json`
- Test: `tests/test_schema_file.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_schema_file.py
import json
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path(__file__).parents[1] / "src" / "afp" / "schema" / "field_report.schema.json"
VECTORS = Path(__file__).parent / "vectors"


def _schema():
    return json.loads(SCHEMA_PATH.read_text())


def test_schema_is_valid_jsonschema():
    jsonschema.Draft202012Validator.check_schema(_schema())


def test_valid_minimal_vector_passes():
    report = json.loads((VECTORS / "valid_minimal.json").read_text())
    jsonschema.validate(report, _schema())


def test_invalid_vector_fails():
    report = json.loads((VECTORS / "invalid_missing_required.json").read_text())
    with __import__("pytest").raises(jsonschema.ValidationError):
        jsonschema.validate(report, _schema())
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `uv run pytest tests/test_schema_file.py -v`
Expected: FAIL con `FileNotFoundError` (el schema aún no existe)

- [ ] **Step 3: Escribir el JSON Schema**

```json
// src/afp/schema/field_report.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://afp.dev/schema/field_report.schema.json",
  "title": "AFP Field Report",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version", "report_id", "subject_uri", "goal", "expectation",
    "observed", "friction_type", "fault_domain", "severity", "timestamp"
  ],
  "properties": {
    "schema_version": { "type": "string", "const": "afp/0.2" },
    "report_id": { "type": "string", "minLength": 1 },
    "subject_uri": { "type": "string", "minLength": 1 },
    "goal": { "type": "string", "minLength": 1 },
    "expectation": { "type": "string", "minLength": 1 },
    "observed": { "type": "string", "minLength": 1 },
    "friction_type": {
      "type": "string",
      "enum": ["bug", "undocumented_behavior", "missing_capability",
               "confusing_interface", "wrong_output", "integration_mismatch"]
    },
    "fault_domain": {
      "type": "string",
      "enum": ["tool", "agent_misuse", "ambiguous_contract", "environment_issue",
               "permission_denied", "rate_limit", "timeout"]
    },
    "severity": { "type": "string", "enum": ["blocked", "degraded", "cosmetic"] },
    "timestamp": { "type": "string", "format": "date-time" },
    "tool_version": { "type": "string" },
    "plan_step": { "type": "string" },
    "workaround": { "type": "string" },
    "inputs_redacted": { "type": "object" },
    "harness": { "type": "string" },
    "harness_version": { "type": "string" },
    "agent_model": { "type": "string" },
    "tool_call_name": { "type": "string" },
    "tool_call_id": { "type": "string" },
    "trace_id": { "type": "string" },
    "contract_ref": { "type": "string" },
    "evidence": { "type": "array" },
    "confidence": { "type": "string", "enum": ["high", "medium", "low"] },
    "reproducibility": {
      "type": "string", "enum": ["deterministic", "intermittent", "once"]
    },
    "dedupe_key": { "type": "string" }
  }
}
```

- [ ] **Step 4: Escribir los vectores de prueba**

```json
// tests/vectors/valid_minimal.json
{
  "schema_version": "afp/0.2",
  "report_id": "afp_test0001",
  "subject_uri": "pkg:npm/eslint@9.2.0",
  "goal": "Auto-arreglar lint antes de commitear",
  "expectation": "--fix corrige y sale con código 0",
  "observed": "Salió con código 1 sin explicar la regla no auto-fixable",
  "friction_type": "confusing_interface",
  "fault_domain": "tool",
  "severity": "degraded",
  "timestamp": "2026-05-30T18:00:00+00:00"
}
```

```json
// tests/vectors/invalid_missing_required.json
{
  "schema_version": "afp/0.2",
  "report_id": "afp_test0002",
  "subject_uri": "pkg:npm/eslint@9.2.0",
  "goal": "Falta expectation, observed, friction_type, etc."
}
```

- [ ] **Step 5: Ejecutar el test para verificar que pasa**

Run: `uv run pytest tests/test_schema_file.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add src/afp/schema/field_report.schema.json tests/vectors/ tests/test_schema_file.py
git commit -m "feat: add field report JSON Schema and test vectors"
```

---

### Task 3: Identidad `subject_uri` (PURL-based)

**Files:**
- Create: `src/afp/identity.py`
- Test: `tests/test_identity.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_identity.py
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
    # esquema pkg con localizador roto debe fallar vía packageurl
    with pytest.raises(InvalidSubjectUri):
        validate_subject_uri("pkg:")
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `uv run pytest tests/test_identity.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'afp.identity'`

- [ ] **Step 3: Escribir la implementación mínima**

```python
# src/afp/identity.py
from packageurl import PackageURL

SUPPORTED_SCHEMES = ("pkg", "https", "http", "mcp", "afp")


class InvalidSubjectUri(ValueError):
    """El subject_uri no respeta ningún esquema soportado por AFP."""


def _scheme_of(uri: str) -> str:
    # pkg: y afp: usan ':'; http(s):// y mcp:// usan '://'
    if "://" in uri:
        return uri.split("://", 1)[0]
    if ":" in uri:
        return uri.split(":", 1)[0]
    return ""


def validate_subject_uri(uri: str) -> str:
    if not uri or not isinstance(uri, str):
        raise InvalidSubjectUri("subject_uri vacío")
    scheme = _scheme_of(uri)
    if scheme not in SUPPORTED_SCHEMES:
        raise InvalidSubjectUri(f"esquema no soportado: {scheme!r}")
    if scheme == "pkg":
        try:
            PackageURL.from_string(uri)
        except ValueError as exc:
            raise InvalidSubjectUri(f"PURL inválido: {exc}") from exc
    else:
        # para http(s)/mcp/afp exigimos algo después del separador
        rest = uri.split("://", 1)[-1] if "://" in uri else uri.split(":", 1)[-1]
        if not rest:
            raise InvalidSubjectUri(f"localizador vacío para {scheme!r}")
    return uri
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `uv run pytest tests/test_identity.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/afp/identity.py tests/test_identity.py
git commit -m "feat: add subject_uri validation backed by PURL"
```

---

### Task 4: Modelo `FieldReport`

**Files:**
- Create: `src/afp/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_models.py
from afp.enums import FaultDomain, FrictionType, Severity
from afp.models import FieldReport


def _kwargs():
    return dict(
        subject_uri="pkg:pypi/ruff",
        goal="lintear el proyecto",
        expectation="salida JSON con la lista de errores",
        observed="salida en texto plano sin estructura",
        friction_type=FrictionType.WRONG_OUTPUT,
        fault_domain=FaultDomain.TOOL,
        severity=Severity.DEGRADED,
    )


def test_create_fills_generated_fields():
    r = FieldReport.create(**_kwargs())
    assert r.report_id.startswith("afp_")
    assert r.schema_version == "afp/0.2"
    assert r.timestamp.endswith("+00:00")


def test_to_dict_drops_none_and_serializes_enums():
    r = FieldReport.create(**_kwargs())
    d = r.to_dict()
    assert d["friction_type"] == "wrong_output"
    assert d["fault_domain"] == "tool"
    assert "workaround" not in d  # None se omite


def test_round_trip_from_dict():
    r = FieldReport.create(**_kwargs(), workaround="parsear a mano")
    d = r.to_dict()
    r2 = FieldReport.from_dict(d)
    assert r2.to_dict() == d
    assert r2.workaround == "parsear a mano"
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'afp.models'`

- [ ] **Step 3: Escribir la implementación mínima**

```python
# src/afp/models.py
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from afp import SCHEMA_VERSION
from afp.enums import (
    Confidence, FaultDomain, FrictionType, Reproducibility, Severity,
)
from afp.identity import validate_subject_uri

_ENUM_FIELDS = {
    "friction_type": FrictionType,
    "fault_domain": FaultDomain,
    "severity": Severity,
    "confidence": Confidence,
    "reproducibility": Reproducibility,
}


@dataclass
class FieldReport:
    # --- core (required) ---
    subject_uri: str
    goal: str
    expectation: str
    observed: str
    friction_type: FrictionType
    fault_domain: FaultDomain
    severity: Severity
    report_id: str = field(default_factory=lambda: "afp_" + uuid4().hex)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    schema_version: str = SCHEMA_VERSION
    # --- extensiones (optional) ---
    tool_version: str | None = None
    plan_step: str | None = None
    workaround: str | None = None
    inputs_redacted: dict | None = None
    harness: str | None = None
    harness_version: str | None = None
    agent_model: str | None = None
    tool_call_name: str | None = None
    tool_call_id: str | None = None
    trace_id: str | None = None
    contract_ref: str | None = None
    evidence: list | None = None
    confidence: Confidence | None = None
    reproducibility: Reproducibility | None = None
    dedupe_key: str | None = None

    @classmethod
    def create(cls, **kwargs) -> "FieldReport":
        validate_subject_uri(kwargs["subject_uri"])
        return cls(**kwargs)

    def to_dict(self) -> dict:
        out: dict = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if value is None:
                continue
            out[f.name] = value.value if isinstance(value, Enum) else value
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "FieldReport":
        data = dict(data)
        for name, enum_cls in _ENUM_FIELDS.items():
            if data.get(name) is not None:
                data[name] = enum_cls(data[name])
        return cls(**data)
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/afp/models.py tests/test_models.py
git commit -m "feat: add FieldReport model with create/to_dict/from_dict"
```

---

### Task 5: Detección de secretos (clase "prohibido")

**Files:**
- Create: `src/afp/redact.py`
- Test: `tests/test_redact.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_redact.py
import pytest

from afp.redact import contains_secret, scan_for_secrets, SecretDetected, assert_no_secrets


@pytest.mark.parametrize("text", [
    "sk-ABCDEFGHIJKLMNOPQRSTUVWX",          # OpenAI-style
    "ghp_0123456789abcdefghijklmnopqrstuvwxyz",  # GitHub PAT
    "AKIAIOSFODNN7EXAMPLE",                  # AWS access key id
    "-----BEGIN PRIVATE KEY-----",          # PEM
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
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `uv run pytest tests/test_redact.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'afp.redact'`

- [ ] **Step 3: Escribir la implementación mínima**

```python
# src/afp/redact.py
import re

# Patrones de la clase "prohibido" (§5 del spec). Lista mínima y ampliable.
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),                 # OpenAI-style
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),                # GitHub PAT
    re.compile(r"AKIA[0-9A-Z]{16}"),                    # AWS access key id
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),  # PEM
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),        # Slack tokens
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
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `uv run pytest tests/test_redact.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/afp/redact.py tests/test_redact.py
git commit -m "feat: add secret detection for forbidden-class PII (hard block)"
```

---

### Task 6: Validación (JSON Schema + hard-block de secretos)

**Files:**
- Create: `src/afp/validate.py`
- Test: `tests/test_validate.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_validate.py
import pytest

from afp.enums import FaultDomain, FrictionType, Severity
from afp.models import FieldReport
from afp.validate import validate_report, ReportInvalid
from afp.redact import SecretDetected


def _report_dict(**extra):
    r = FieldReport.create(
        subject_uri="pkg:pypi/ruff",
        goal="lintear",
        expectation="salida JSON",
        observed="texto plano",
        friction_type=FrictionType.WRONG_OUTPUT,
        fault_domain=FaultDomain.TOOL,
        severity=Severity.DEGRADED,
        **extra,
    )
    return r.to_dict()


def test_valid_report_passes():
    validate_report(_report_dict())  # no raise


def test_missing_required_fails():
    bad = _report_dict()
    del bad["goal"]
    with pytest.raises(ReportInvalid):
        validate_report(bad)


def test_bad_enum_fails():
    bad = _report_dict()
    bad["severity"] = "catastrophic"
    with pytest.raises(ReportInvalid):
        validate_report(bad)


def test_secret_in_report_blocks():
    bad = _report_dict(workaround="usé ghp_0123456789abcdefghijklmnopqrstuvwxyz")
    with pytest.raises(SecretDetected):
        validate_report(bad)
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `uv run pytest tests/test_validate.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'afp.validate'`

- [ ] **Step 3: Escribir la implementación mínima**

```python
# src/afp/validate.py
import json
from functools import lru_cache
from pathlib import Path

import jsonschema

from afp.redact import assert_no_secrets

_SCHEMA_PATH = Path(__file__).parent / "schema" / "field_report.schema.json"


class ReportInvalid(Exception):
    """El reporte no cumple el JSON Schema de AFP."""


@lru_cache(maxsize=1)
def load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())


def validate_report(report: dict) -> None:
    """Valida contra el JSON Schema y bloquea si hay secretos.

    Orden: primero el hard-block de secretos (§5), luego el schema.
    """
    assert_no_secrets(report)
    try:
        jsonschema.validate(report, load_schema())
    except jsonschema.ValidationError as exc:
        raise ReportInvalid(exc.message) from exc
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `uv run pytest tests/test_validate.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/afp/validate.py tests/test_validate.py
git commit -m "feat: add report validation (schema + secret hard-block)"
```

---

### Task 7: Manifiesto `afp.json`

**Files:**
- Create: `src/afp/schema/afp_manifest.schema.json`
- Create: `src/afp/manifest.py`
- Test: `tests/test_manifest.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_manifest.py
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
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `uv run pytest tests/test_manifest.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'afp.manifest'`

- [ ] **Step 3: Escribir el JSON Schema del manifiesto**

```json
// src/afp/schema/afp_manifest.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://afp.dev/schema/afp_manifest.schema.json",
  "title": "AFP Manifest (afp.json)",
  "type": "object",
  "additionalProperties": false,
  "required": ["afp_version", "subject_uri", "sink"],
  "properties": {
    "afp_version": { "type": "string" },
    "subject_uri": { "type": "string", "minLength": 1 },
    "sink": {
      "type": "object",
      "required": ["type"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["github_issues", "gitlab_issues", "file", "http", "local", "draft"]
        },
        "repo": { "type": "string" },
        "label": { "type": "string" },
        "path": { "type": "string" },
        "url": { "type": "string" }
      }
    },
    "redaction": { "type": "string", "enum": ["required", "optional"] },
    "accepts_remote": { "type": "boolean" },
    "schema_extensions": { "type": "array" }
  }
}
```

- [ ] **Step 4: Escribir la implementación mínima**

```python
# src/afp/manifest.py
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import jsonschema

_SCHEMA_PATH = Path(__file__).parent / "schema" / "afp_manifest.schema.json"


class ManifestInvalid(Exception):
    """El afp.json no cumple su JSON Schema."""


@lru_cache(maxsize=1)
def _schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())


@dataclass
class Manifest:
    afp_version: str
    subject_uri: str
    sink: dict
    redaction: str = "required"
    accepts_remote: bool = False
    schema_extensions: list | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Manifest":
        try:
            jsonschema.validate(data, _schema())
        except jsonschema.ValidationError as exc:
            raise ManifestInvalid(exc.message) from exc
        return cls(
            afp_version=data["afp_version"],
            subject_uri=data["subject_uri"],
            sink=data["sink"],
            redaction=data.get("redaction", "required"),
            accepts_remote=data.get("accepts_remote", False),
            schema_extensions=data.get("schema_extensions"),
        )


def load_manifest(path: Path) -> Manifest:
    return Manifest.from_dict(json.loads(Path(path).read_text()))
```

- [ ] **Step 5: Ejecutar el test para verificar que pasa**

Run: `uv run pytest tests/test_manifest.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add src/afp/schema/afp_manifest.schema.json src/afp/manifest.py tests/test_manifest.py
git commit -m "feat: add afp.json manifest schema and parser"
```

---

### Task 8: Descubrimiento + decisión de routing

**Files:**
- Create: `src/afp/discovery.py`
- Test: `tests/test_discovery.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_discovery.py
import json

from afp.discovery import discover, RoutingDecision


def test_no_manifest_returns_local_and_draft_only(tmp_path):
    decision = discover(tmp_path)
    assert isinstance(decision, RoutingDecision)
    assert decision.has_manifest is False
    assert decision.manifest is None
    assert set(decision.allowed_sinks) == {"local", "draft"}


def test_root_manifest_allows_declared_remote(tmp_path):
    (tmp_path / "afp.json").write_text(json.dumps({
        "afp_version": "0.2",
        "subject_uri": "mcp://github.com/user/repo",
        "sink": {"type": "github_issues", "repo": "user/repo", "label": "afp-report"},
        "accepts_remote": True,
    }))
    decision = discover(tmp_path)
    assert decision.has_manifest is True
    assert "github_issues" in decision.allowed_sinks
    assert "local" in decision.allowed_sinks  # local siempre permitido


def test_well_known_manifest_is_found(tmp_path):
    wk = tmp_path / ".well-known"
    wk.mkdir()
    (wk / "afp.json").write_text(json.dumps({
        "afp_version": "0.2",
        "subject_uri": "https://api.example.com",
        "sink": {"type": "http", "url": "https://api.example.com/afp"},
        "accepts_remote": True,
    }))
    decision = discover(tmp_path)
    assert decision.has_manifest is True
    assert "http" in decision.allowed_sinks


def test_manifest_without_accepts_remote_blocks_remote(tmp_path):
    (tmp_path / "afp.json").write_text(json.dumps({
        "afp_version": "0.2",
        "subject_uri": "mcp://github.com/user/repo",
        "sink": {"type": "github_issues", "repo": "user/repo"},
        "accepts_remote": False,
    }))
    decision = discover(tmp_path)
    assert set(decision.allowed_sinks) == {"local", "draft"}
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `uv run pytest tests/test_discovery.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'afp.discovery'`

- [ ] **Step 3: Escribir la implementación mínima**

```python
# src/afp/discovery.py
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
    if manifest.accepts_remote:
        allowed.append(manifest.sink["type"])
    return RoutingDecision(True, manifest, allowed)
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `uv run pytest tests/test_discovery.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/afp/discovery.py tests/test_discovery.py
git commit -m "feat: add manifest discovery + routing policy (no manifest = local/draft only)"
```

---

### Task 9: Sink base + LocalSink

**Files:**
- Create: `src/afp/sinks/base.py`
- Create: `src/afp/sinks/local.py`
- Test: `tests/test_sinks_local.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_sinks_local.py
import json

from afp.sinks.local import LocalSink


def test_local_sink_appends_jsonl(tmp_path):
    sink = LocalSink(base_dir=tmp_path)
    ref1 = sink.submit({"report_id": "afp_1", "goal": "a"})
    ref2 = sink.submit({"report_id": "afp_2", "goal": "b"})
    spool = tmp_path / ".afp" / "reports.jsonl"
    assert spool.exists()
    lines = spool.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["report_id"] == "afp_1"
    assert str(spool) in ref1 and str(spool) in ref2
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `uv run pytest tests/test_sinks_local.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'afp.sinks.local'`

- [ ] **Step 3: Escribir la base y el LocalSink**

```python
# src/afp/sinks/base.py
class Sink:
    """Interfaz común de los sinks AFP."""

    name: str = "base"

    def submit(self, report: dict) -> str:
        """Deposita el reporte y devuelve una referencia (ruta o URL)."""
        raise NotImplementedError
```

```python
# src/afp/sinks/local.py
import json
from pathlib import Path

from afp.sinks.base import Sink


class LocalSink(Sink):
    name = "local"

    def __init__(self, base_dir: Path = Path(".")):
        self.spool = Path(base_dir) / ".afp" / "reports.jsonl"

    def submit(self, report: dict) -> str:
        self.spool.parent.mkdir(parents=True, exist_ok=True)
        with self.spool.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False) + "\n")
        return f"local:{self.spool}"
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `uv run pytest tests/test_sinks_local.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/afp/sinks/base.py src/afp/sinks/local.py tests/test_sinks_local.py
git commit -m "feat: add Sink base and LocalSink (jsonl spool)"
```

---

### Task 10: DraftSink

**Files:**
- Create: `src/afp/sinks/draft.py`
- Test: `tests/test_sinks_draft.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_sinks_draft.py
import json

from afp.sinks.draft import DraftSink


def test_draft_sink_writes_one_file_per_report(tmp_path):
    sink = DraftSink(base_dir=tmp_path)
    ref = sink.submit({"report_id": "afp_abc", "goal": "x"})
    draft = tmp_path / ".afp" / "drafts" / "afp_abc.json"
    assert draft.exists()
    assert json.loads(draft.read_text())["goal"] == "x"
    assert "afp_abc" in ref


def test_draft_sink_handles_missing_report_id(tmp_path):
    sink = DraftSink(base_dir=tmp_path)
    ref = sink.submit({"goal": "sin id"})
    drafts = list((tmp_path / ".afp" / "drafts").glob("*.json"))
    assert len(drafts) == 1
    assert "draft" in ref.lower() or drafts[0].stem in ref
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `uv run pytest tests/test_sinks_draft.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'afp.sinks.draft'`

- [ ] **Step 3: Escribir el DraftSink**

```python
# src/afp/sinks/draft.py
import json
from pathlib import Path
from uuid import uuid4

from afp.sinks.base import Sink


class DraftSink(Sink):
    """Escribe un borrador para revisión humana ANTES de enviarse a ningún sitio."""

    name = "draft"

    def __init__(self, base_dir: Path = Path(".")):
        self.dir = Path(base_dir) / ".afp" / "drafts"

    def submit(self, report: dict) -> str:
        self.dir.mkdir(parents=True, exist_ok=True)
        report_id = report.get("report_id") or f"draft_{uuid4().hex}"
        path = self.dir / f"{report_id}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"draft:{path}"
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `uv run pytest tests/test_sinks_draft.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/afp/sinks/draft.py tests/test_sinks_draft.py
git commit -m "feat: add DraftSink (human-confirmation drafts)"
```

---

### Task 11: GitHubIssuesSink (vía `gh` CLI)

**Files:**
- Create: `src/afp/sinks/github.py`
- Test: `tests/test_sinks_github.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_sinks_github.py
from unittest.mock import patch
import subprocess

import pytest

from afp.sinks.github import GitHubIssuesSink


def test_github_sink_calls_gh_and_returns_url():
    sink = GitHubIssuesSink(repo="user/repo", label="afp-report")
    fake = subprocess.CompletedProcess(
        args=["gh"], returncode=0,
        stdout="https://github.com/user/repo/issues/42\n", stderr="",
    )
    with patch("afp.sinks.github.subprocess.run", return_value=fake) as run:
        ref = sink.submit({
            "report_id": "afp_x", "subject_uri": "pkg:npm/eslint@9.2.0",
            "friction_type": "bug", "severity": "blocked", "goal": "g",
            "expectation": "e", "observed": "o",
        })
    assert ref == "https://github.com/user/repo/issues/42"
    args = run.call_args.args[0]
    assert args[:3] == ["gh", "issue", "create"]
    assert "--repo" in args and "user/repo" in args
    assert "--label" in args and "afp-report" in args


def test_github_sink_raises_on_failure():
    sink = GitHubIssuesSink(repo="user/repo", label="afp-report")
    fake = subprocess.CompletedProcess(args=["gh"], returncode=1, stdout="", stderr="boom")
    with patch("afp.sinks.github.subprocess.run", return_value=fake):
        with pytest.raises(RuntimeError):
            sink.submit({"report_id": "afp_x", "goal": "g"})
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `uv run pytest tests/test_sinks_github.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'afp.sinks.github'`

- [ ] **Step 3: Escribir el GitHubIssuesSink**

```python
# src/afp/sinks/github.py
import json
import subprocess

from afp.sinks.base import Sink


class GitHubIssuesSink(Sink):
    name = "github_issues"

    def __init__(self, repo: str, label: str = "afp-report"):
        self.repo = repo
        self.label = label

    def _title(self, report: dict) -> str:
        ft = report.get("friction_type", "friction")
        subj = report.get("subject_uri", "unknown-tool")
        return f"[AFP/{ft}] {subj}"

    def _body(self, report: dict) -> str:
        return (
            "Field report generado por un agente vía AFP.\n\n"
            "```json\n" + json.dumps(report, ensure_ascii=False, indent=2) + "\n```"
        )

    def submit(self, report: dict) -> str:
        cmd = [
            "gh", "issue", "create",
            "--repo", self.repo,
            "--label", self.label,
            "--title", self._title(report),
            "--body", self._body(report),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"gh issue create falló: {result.stderr.strip()}")
        return result.stdout.strip()
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `uv run pytest tests/test_sinks_github.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/afp/sinks/github.py tests/test_sinks_github.py
git commit -m "feat: add GitHubIssuesSink via gh CLI"
```

---

### Task 12: Factoría de sinks + enforcement de routing

**Files:**
- Modify: `src/afp/sinks/__init__.py`
- Test: `tests/test_routing.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_routing.py
import pytest

from afp.discovery import RoutingDecision
from afp.manifest import Manifest
from afp.sinks import get_sink, route, SinkNotAllowed
from afp.sinks.local import LocalSink
from afp.sinks.github import GitHubIssuesSink


def test_get_sink_local(tmp_path):
    sink = get_sink("local", base_dir=tmp_path)
    assert isinstance(sink, LocalSink)


def test_get_sink_unknown_raises():
    with pytest.raises(ValueError):
        get_sink("carrier_pigeon")


def test_route_blocks_remote_without_manifest(tmp_path):
    decision = RoutingDecision(has_manifest=False, manifest=None, allowed_sinks=["local", "draft"])
    with pytest.raises(SinkNotAllowed):
        route("github_issues", decision, base_dir=tmp_path)


def test_route_allows_remote_with_manifest(tmp_path):
    manifest = Manifest(
        afp_version="0.2", subject_uri="mcp://github.com/user/repo",
        sink={"type": "github_issues", "repo": "user/repo", "label": "afp-report"},
        accepts_remote=True,
    )
    decision = RoutingDecision(True, manifest, ["local", "draft", "github_issues"])
    sink = route("github_issues", decision, base_dir=tmp_path)
    assert isinstance(sink, GitHubIssuesSink)
    assert sink.repo == "user/repo"


def test_route_defaults_to_draft_when_none_requested(tmp_path):
    decision = RoutingDecision(False, None, ["local", "draft"])
    sink = route(None, decision, base_dir=tmp_path)
    assert sink.name == "draft"
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `uv run pytest tests/test_routing.py -v`
Expected: FAIL con `ImportError` (route/get_sink/SinkNotAllowed no existen)

- [ ] **Step 3: Escribir la factoría y el enforcement**

```python
# src/afp/sinks/__init__.py
from pathlib import Path

from afp.sinks.draft import DraftSink
from afp.sinks.github import GitHubIssuesSink
from afp.sinks.local import LocalSink

LOCAL_SINKS = {"local", "draft"}
REMOTE_SINKS = {"github_issues", "gitlab_issues", "file", "http"}


class SinkNotAllowed(Exception):
    """Se pidió un sink remoto que la política de routing no permite."""


def get_sink(sink_type: str, *, base_dir: Path = Path("."), manifest=None):
    if sink_type == "local":
        return LocalSink(base_dir=base_dir)
    if sink_type == "draft":
        return DraftSink(base_dir=base_dir)
    if sink_type == "github_issues":
        if manifest is None:
            raise ValueError("github_issues requiere un manifest con repo/label")
        return GitHubIssuesSink(
            repo=manifest.sink["repo"],
            label=manifest.sink.get("label", "afp-report"),
        )
    raise ValueError(f"sink desconocido: {sink_type!r}")


def route(requested, decision, *, base_dir: Path = Path(".")):
    """Elige un sink respetando la decisión de routing.

    - requested None  -> 'draft' (siempre seguro).
    - requested no permitido por la política -> SinkNotAllowed.
    """
    chosen = requested or "draft"
    if chosen not in decision.allowed_sinks:
        raise SinkNotAllowed(
            f"sink {chosen!r} no permitido; permitidos: {decision.allowed_sinks}"
        )
    return get_sink(chosen, base_dir=base_dir, manifest=decision.manifest)
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `uv run pytest tests/test_routing.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/afp/sinks/__init__.py tests/test_routing.py
git commit -m "feat: add sink factory + routing enforcement (remote requires manifest)"
```

---

### Task 13: CLI (`typer`): validate / report / submit

**Files:**
- Create: `src/afp/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_cli.py
import json

from typer.testing import CliRunner

from afp.cli import app

runner = CliRunner()


def _partial(**extra):
    base = {
        "subject_uri": "pkg:pypi/ruff",
        "goal": "lintear",
        "expectation": "salida JSON",
        "observed": "texto plano",
        "friction_type": "wrong_output",
        "fault_domain": "tool",
        "severity": "degraded",
    }
    base.update(extra)
    return base


def test_report_builds_valid_report(tmp_path):
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(_partial()))
    out = tmp_path / "report.json"
    result = runner.invoke(app, ["report", "--from", str(src), "--out", str(out)])
    assert result.exit_code == 0, result.output
    report = json.loads(out.read_text())
    assert report["report_id"].startswith("afp_")
    assert report["schema_version"] == "afp/0.2"


def test_validate_ok(tmp_path):
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(_partial()))
    out = tmp_path / "report.json"
    runner.invoke(app, ["report", "--from", str(src), "--out", str(out)])
    result = runner.invoke(app, ["validate", str(out)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_validate_rejects_secret(tmp_path):
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(_partial(workaround="ghp_0123456789abcdefghijklmnopqrstuvwxyz")))
    out = tmp_path / "report.json"
    runner.invoke(app, ["report", "--from", str(src), "--out", str(out)])
    result = runner.invoke(app, ["validate", str(out)])
    assert result.exit_code != 0


def test_submit_without_manifest_goes_to_draft(tmp_path):
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(_partial()))
    out = tmp_path / "report.json"
    runner.invoke(app, ["report", "--from", str(src), "--out", str(out)])
    result = runner.invoke(
        app, ["submit", str(out), "--dir", str(tmp_path), "--sink", "github_issues"]
    )
    # github_issues no permitido sin manifest -> error claro
    assert result.exit_code != 0
    assert "no permitido" in result.output.lower() or "not allowed" in result.output.lower()


def test_submit_local_ok(tmp_path):
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(_partial()))
    out = tmp_path / "report.json"
    runner.invoke(app, ["report", "--from", str(src), "--out", str(out)])
    result = runner.invoke(app, ["submit", str(out), "--dir", str(tmp_path), "--sink", "local"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".afp" / "reports.jsonl").exists()
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'afp.cli'`

- [ ] **Step 3: Escribir la CLI**

```python
# src/afp/cli.py
import json
from pathlib import Path

import typer

from afp.discovery import discover
from afp.models import FieldReport
from afp.redact import SecretDetected
from afp.sinks import SinkNotAllowed, route
from afp.validate import ReportInvalid, validate_report

app = typer.Typer(help="AFP — Agent Feedback Protocol CLI")


@app.command()
def report(
    from_: Path = typer.Option(..., "--from", help="JSON parcial con los campos del reporte"),
    out: Path = typer.Option(None, "--out", help="Dónde escribir el reporte completo"),
):
    """Construye un field report completo (añade id/timestamp/schema_version) y lo valida."""
    partial = json.loads(Path(from_).read_text())
    if "report_id" in partial:
        fr = FieldReport.from_dict(partial)
    else:
        fr = FieldReport.create(**partial)
    data = fr.to_dict()
    try:
        validate_report(data)
    except (ReportInvalid, SecretDetected) as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        typer.echo(f"OK: reporte escrito en {out}")
    else:
        typer.echo(text)


@app.command()
def validate(path: Path = typer.Argument(..., help="Reporte JSON a validar")):
    """Valida un field report contra el JSON Schema + hard-block de secretos."""
    data = json.loads(Path(path).read_text())
    try:
        validate_report(data)
    except (ReportInvalid, SecretDetected) as exc:
        typer.echo(f"INVALID: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo("OK: reporte válido")


@app.command()
def submit(
    path: Path = typer.Argument(..., help="Reporte JSON ya validado"),
    dir_: Path = typer.Option(Path("."), "--dir", help="Directorio donde buscar afp.json"),
    sink: str = typer.Option(None, "--sink", help="Sink solicitado (local/draft/github_issues)"),
):
    """Descubre el buzón de la tool y deposita el reporte respetando la política de routing."""
    data = json.loads(Path(path).read_text())
    try:
        validate_report(data)
    except (ReportInvalid, SecretDetected) as exc:
        typer.echo(f"INVALID: {exc}", err=True)
        raise typer.Exit(code=1)
    decision = discover(dir_)
    try:
        chosen = route(sink, decision, base_dir=dir_)
    except SinkNotAllowed as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1)
    ref = chosen.submit(data)
    typer.echo(f"OK: depositado vía {chosen.name} -> {ref}")
```

> **Nota:** `FieldReport.create(**partial)` no convierte los strings de enum a
> objetos `Enum`, pero no hace falta: el dataclass los almacena tal cual y
> `to_dict()` solo convierte cuando el valor *ya* es `Enum`, así que la salida
> JSON queda correcta (`"friction_type": "wrong_output"`). `validate_report`
> valida ese JSON contra el schema. El camino normal (sin `report_id` en el
> parcial) es `create`; `from_dict` solo se usa si el parcial ya trae `report_id`.

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/afp/cli.py tests/test_cli.py
git commit -m "feat: add AFP CLI (report / validate / submit)"
```

---

### Task 14: Fixture compartida + test end-to-end

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_e2e.py`

- [ ] **Step 1: Escribir `conftest.py` y el test e2e que falla**

```python
# tests/conftest.py
import pytest

from afp.enums import FaultDomain, FrictionType, Severity
from afp.models import FieldReport


@pytest.fixture
def minimal_report() -> dict:
    return FieldReport.create(
        subject_uri="pkg:pypi/ruff",
        goal="lintear el proyecto",
        expectation="salida JSON con errores",
        observed="texto plano",
        friction_type=FrictionType.WRONG_OUTPUT,
        fault_domain=FaultDomain.TOOL,
        severity=Severity.DEGRADED,
    ).to_dict()
```

```python
# tests/test_e2e.py
import json

from afp.discovery import discover
from afp.sinks import route
from afp.validate import validate_report


def test_full_flow_no_manifest_lands_in_draft(tmp_path, minimal_report):
    # 1. válido
    validate_report(minimal_report)
    # 2. descubrir buzón (sin manifiesto)
    decision = discover(tmp_path)
    assert decision.allowed_sinks == ["local", "draft"]
    # 3. enrutar (sin sink pedido -> draft) y depositar
    sink = route(None, decision, base_dir=tmp_path)
    ref = sink.submit(minimal_report)
    # 4. el borrador existe y es legible
    assert ref.startswith("draft:")
    drafts = list((tmp_path / ".afp" / "drafts").glob("*.json"))
    assert len(drafts) == 1
    assert json.loads(drafts[0].read_text())["subject_uri"] == "pkg:pypi/ruff"


def test_full_flow_with_manifest_allows_local(tmp_path, minimal_report):
    (tmp_path / "afp.json").write_text(json.dumps({
        "afp_version": "0.2",
        "subject_uri": "pkg:pypi/ruff",
        "sink": {"type": "github_issues", "repo": "astral-sh/ruff", "label": "afp-report"},
        "accepts_remote": True,
    }))
    decision = discover(tmp_path)
    assert "github_issues" in decision.allowed_sinks
    # depositamos en local (siempre permitido) para no llamar a gh en el test
    sink = route("local", decision, base_dir=tmp_path)
    ref = sink.submit(minimal_report)
    assert ref.startswith("local:")
    assert (tmp_path / ".afp" / "reports.jsonl").exists()
```

- [ ] **Step 2: Ejecutar el test para ver que falla**

Run: `uv run pytest tests/test_e2e.py -v`
Expected: FAIL (si conftest aún no aporta la fixture o el flujo tiene un gap). Si ya pasa, confirma que el flujo completo funciona.

- [ ] **Step 3: Si falla, ajustar el código mínimo necesario**

No debería requerir código nuevo: el flujo usa piezas ya implementadas. Si falla, leer el error y corregir la pieza señalada (no añadir lógica nueva aquí).

- [ ] **Step 4: Ejecutar toda la suite**

Run: `uv run pytest -v`
Expected: PASS (todos los tests de todas las tareas)

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/test_e2e.py
git commit -m "test: add shared fixture and end-to-end flow tests"
```

---

### Task 15: README de uso

**Files:**
- Create: `README.md`

- [ ] **Step 1: Escribir el README**

````markdown
# AFP — Agent Feedback Protocol (reference implementation)

Implementación de referencia en Python del **camino de vuelta** que le falta a MCP:
un canal estándar para que un agente de IA reporte la *fricción* que encontró al
usar una herramienta, dirigido al mantenedor de esa herramienta.

Spec: `docs/superpowers/specs/2026-05-30-afp-protocol-design.md`

## Instalación

```bash
uv sync
```

## Uso de la CLI

```bash
# 1. Construir un field report completo a partir de un JSON parcial
uv run afp report --from partial.json --out report.json

# 2. Validar (JSON Schema + hard-block de secretos)
uv run afp validate report.json

# 3. Depositar respetando la política de routing
#    Sin afp.json en --dir, solo se permite local/draft (nunca auto-envío remoto).
uv run afp submit report.json --dir . --sink draft
```

`partial.json` mínimo:

```json
{
  "subject_uri": "pkg:pypi/ruff",
  "goal": "lintear el proyecto",
  "expectation": "salida JSON con los errores",
  "observed": "salida en texto plano sin estructura",
  "friction_type": "wrong_output",
  "fault_domain": "tool",
  "severity": "degraded"
}
```

## Regla de oro de seguridad

Sin un `afp.json` declarado por la tool, AFP **nunca** auto-envía a un repo de
terceros: solo escribe en `local` (spool) o `draft` (revisión humana). El envío
remoto (p.ej. `github_issues`) es siempre **opt-in del mantenedor**.

## Tests

```bash
uv run pytest -v
```
````

- [ ] **Step 2: Verificar que la CLI funciona de verdad (smoke test manual)**

```bash
printf '%s' '{"subject_uri":"pkg:pypi/ruff","goal":"g","expectation":"e","observed":"o","friction_type":"bug","fault_domain":"tool","severity":"blocked"}' > /tmp/partial.json
uv run afp report --from /tmp/partial.json --out /tmp/report.json
uv run afp validate /tmp/report.json
uv run afp submit /tmp/report.json --dir /tmp --sink draft
```
Expected: tres comandos terminan en `OK`, y existe `/tmp/.afp/drafts/<id>.json`.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with CLI usage and safety rule"
```

---

## Notas para el implementador

- **TDD estricto:** cada tarea es test→fallo→impl→verde→commit. No saltes el paso de ver el test fallar.
- **DRY:** reutiliza `FieldReport`, `validate_report` y `route` en la CLI; no reimplementes lógica.
- **YAGNI:** no añadas sinks `file`/`http` ni inferencia de repo en este plan; están marcados como follow-up.
- **Imports relativos al paquete:** todo bajo `src/afp/`, importado como `afp.*` (el layout src ya está configurado en `pyproject.toml`).
- **Determinismo de tests:** los tests de `github` mockean `subprocess.run`; nunca llaman a `gh` de verdad.
