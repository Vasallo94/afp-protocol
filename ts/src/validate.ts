/** Field report and manifest validation (SPEC §4, §6, §8). */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { Ajv2020, type ValidateFunction } from "ajv/dist/2020.js";

import { ManifestInvalid, ReportInvalid, InvalidSubjectUri } from "./errors.js";
import { validateSubjectUri } from "./identity.js";
import { assertNoSecrets, redactPii } from "./redact.js";

// Vendored copies of the canonical schemas (spec/schemas/); the Python suite's
// test_spec_sync.py guards that every vendored copy matches the canonical one.
const SCHEMAS_DIR = join(dirname(fileURLToPath(import.meta.url)), "..", "schemas");

/** Strict RFC 3339 date-time: time component and UTC offset are REQUIRED. */
const DATE_TIME = /^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$/;

function isStrictDateTime(value: string): boolean {
  if (!DATE_TIME.test(value)) return false;
  return !Number.isNaN(Date.parse(value));
}

function compile(filename: string): ValidateFunction {
  const ajv = new Ajv2020({ allErrors: false });
  ajv.addFormat("date-time", isStrictDateTime);
  const schema = JSON.parse(readFileSync(join(SCHEMAS_DIR, filename), "utf-8"));
  return ajv.compile(schema);
}

let reportValidator: ValidateFunction | undefined;
let manifestValidator: ValidateFunction | undefined;

function firstError(validate: ValidateFunction): string {
  const err = validate.errors?.[0];
  return err ? `${err.instancePath || "/"} ${err.message ?? "invalid"}` : "invalid";
}

/**
 * Redacts direct PII, hard-blocks secrets, and validates the report
 * (mutates `report` in place, like the Python reference).
 *
 * Order (SPEC §8): redact email PII first — so whatever gets deposited is
 * already clean — then the secret hard-block, then JSON Schema, then the
 * semantic subject_uri check.
 */
export function validateReport(report: Record<string, unknown>): void {
  const redacted = redactPii(report);
  for (const key of Object.keys(report)) delete report[key];
  Object.assign(report, redacted);
  assertNoSecrets(report);
  reportValidator ??= compile("field_report.schema.json");
  if (!reportValidator(report)) {
    throw new ReportInvalid(firstError(reportValidator));
  }
  try {
    validateSubjectUri(report["subject_uri"]);
  } catch (exc) {
    if (exc instanceof InvalidSubjectUri) {
      throw new ReportInvalid(`invalid subject_uri: ${exc.message}`);
    }
    throw exc;
  }
}

export interface Manifest {
  afp_version: string;
  subject_uri: string;
  sink: Record<string, unknown> & { type: string };
  redaction: "required" | "optional";
  accepts_remote: boolean;
  schema_extensions: unknown[] | null;
}

/** Validates an afp.json manifest object and returns it with defaults applied. */
export function validateManifest(data: Record<string, unknown>): Manifest {
  manifestValidator ??= compile("afp_manifest.schema.json");
  if (!manifestValidator(data)) {
    throw new ManifestInvalid(firstError(manifestValidator));
  }
  try {
    validateSubjectUri(data["subject_uri"]);
  } catch (exc) {
    if (exc instanceof InvalidSubjectUri) {
      throw new ManifestInvalid(`invalid subject_uri: ${exc.message}`);
    }
    throw exc;
  }
  return {
    afp_version: data["afp_version"] as string,
    subject_uri: data["subject_uri"] as string,
    sink: data["sink"] as Manifest["sink"],
    redaction: (data["redaction"] as Manifest["redaction"]) ?? "required",
    accepts_remote: (data["accepts_remote"] as boolean) ?? false,
    schema_extensions: (data["schema_extensions"] as unknown[]) ?? null,
  };
}
