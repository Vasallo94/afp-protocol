/**
 * Runs the language-agnostic conformance vectors (spec/vectors/) against the
 * TypeScript implementation. Same contract as the Python reference runner
 * (tests/test_conformance_vectors.py): both implementations must pass the
 * exact same vectors.
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import {
  redactPii,
  scanForSecrets,
  subjectIsOwnedBy,
  validateManifest,
  validateReport,
} from "../src/index.js";

const VECTORS = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "spec", "vectors");

function cases(filename: string): any[] {
  return JSON.parse(readFileSync(join(VECTORS, filename), "utf-8"));
}

describe("field report vectors", () => {
  for (const c of cases("field_report.json")) {
    it(c.description, () => {
      const report = structuredClone(c.data);
      if (c.valid) {
        expect(() => validateReport(report)).not.toThrow();
      } else {
        expect(() => validateReport(report)).toThrow();
      }
    });
  }
});

describe("manifest vectors", () => {
  for (const c of cases("manifest.json")) {
    it(c.description, () => {
      if (c.valid) {
        expect(() => validateManifest(c.data)).not.toThrow();
      } else {
        expect(() => validateManifest(c.data)).toThrow();
      }
    });
  }
});

describe("ownership vectors", () => {
  for (const c of cases("ownership.json")) {
    it(c.description, () => {
      expect(subjectIsOwnedBy(c.report_subject, c.manifest_subject)).toBe(c.owned);
    });
  }
});

describe("redaction vectors", () => {
  for (const c of cases("redaction.json")) {
    it(c.description, () => {
      if (c.outcome === "secret_block") {
        expect(scanForSecrets(c.data).sort()).toEqual([...c.offending_fields].sort());
      } else {
        expect(scanForSecrets(c.data)).toEqual([]);
        expect(redactPii(c.data)).toEqual(c.expected);
      }
    });
  }
});
