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
    # --- forward-compat (ADR-0001) ---
    # Campos de extensión de versiones más nuevas que esta lib no conoce. Se
    # preservan tal cual en vez de descartarse o romper, para que productor y
    # consumidor evolucionen a ritmos distintos.
    extra: dict = field(default_factory=dict)

    @classmethod
    def create(cls, **kwargs) -> "FieldReport":
        validate_subject_uri(kwargs["subject_uri"])
        return cls(**kwargs)

    def to_dict(self) -> dict:
        out: dict = {}
        for f in fields(self):
            if f.name == "extra":
                continue
            value = getattr(self, f.name)
            if value is None:
                continue
            out[f.name] = value.value if isinstance(value, Enum) else value
        out.update(self.extra)
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "FieldReport":
        data = dict(data)
        if "subject_uri" in data:
            validate_subject_uri(data["subject_uri"])
        for name, enum_cls in _ENUM_FIELDS.items():
            if data.get(name) is not None:
                data[name] = enum_cls(data[name])
        known = {f.name for f in fields(cls)} - {"extra"}
        extra = {k: data.pop(k) for k in list(data) if k not in known}
        return cls(**data, extra=extra)
