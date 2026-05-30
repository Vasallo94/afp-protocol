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
