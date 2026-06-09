/** Secret hard-block and direct-PII redaction (SPEC §8).
 *
 * Two distinct treatments:
 * - prohibited class (tokens, keys, JWT, Bearer): hard block — if detected,
 *   the deposit must be aborted (`assertNoSecrets`).
 * - direct PII (email): does NOT abort; it is redacted and the report
 *   continues (`redactPii`).
 */
import { SecretDetected } from "./errors.js";

const SECRET_PATTERNS: RegExp[] = [
  /sk-[A-Za-z0-9]{20,}/, // OpenAI-style
  /ghp_[A-Za-z0-9]{30,}/, // GitHub PAT
  /AKIA[0-9A-Z]{16}/, // AWS access key id
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/, // PEM
  /xox[baprs]-[A-Za-z0-9-]{10,}/, // Slack tokens
  /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{6,}/, // JWT
  /bearer\s+[A-Za-z0-9._\-]{20,}/i, // Bearer token
  /(api[_-]?key|secret|password|access[_-]?key|token)\s*[:=]\s*['"]?[A-Za-z0-9/_\-]{8,}/i, // key=value secret
];

// Email: the domain requires a dot-separated TLD so a PURL `@version`
// (e.g. eslint@9.2.0) is not mistaken for an address.
const EMAIL_PATTERN = /[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}/g;
const EMAIL_PLACEHOLDER = "[REDACTED_EMAIL]";

export function containsSecret(text: unknown): boolean {
  if (typeof text !== "string") return false;
  return SECRET_PATTERNS.some((p) => p.test(text));
}

function* walkStrings(value: unknown): Generator<string> {
  if (typeof value === "string") {
    yield value;
  } else if (Array.isArray(value)) {
    for (const v of value) yield* walkStrings(v);
  } else if (value !== null && typeof value === "object") {
    for (const v of Object.values(value)) yield* walkStrings(v);
  }
}

/** Returns the top-level fields whose values (at any depth) contain secrets. */
export function scanForSecrets(report: Record<string, unknown>): string[] {
  const offending: string[] = [];
  for (const [key, value] of Object.entries(report)) {
    for (const s of walkStrings(value)) {
      if (containsSecret(s)) {
        offending.push(key);
        break;
      }
    }
  }
  return offending;
}

export function assertNoSecrets(report: Record<string, unknown>): void {
  const offending = scanForSecrets(report);
  if (offending.length > 0) {
    throw new SecretDetected(`secrets detected in fields: [${offending.join(", ")}]`);
  }
}

function redactValue(value: unknown): unknown {
  if (typeof value === "string") return value.replace(EMAIL_PATTERN, EMAIL_PLACEHOLDER);
  if (Array.isArray(value)) return value.map(redactValue);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([k, v]) => [k, redactValue(v)]),
    );
  }
  return value;
}

/** Returns a copy of the report with direct PII (email) redacted. */
export function redactPii(report: Record<string, unknown>): Record<string, unknown> {
  return redactValue(report) as Record<string, unknown>;
}
