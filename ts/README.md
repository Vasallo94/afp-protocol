# afp-core (TypeScript)

TypeScript implementation of the [Agent Feedback Protocol](../spec/SPEC.md):
field-report and manifest validation, `subject_uri` identity, ownership
verification (anti-spoofing), and secret/PII redaction.

It passes the same [conformance test vectors](../spec/vectors/) as the Python
reference implementation — that, not shared code, is what makes the two
interoperable.

```ts
import { validateReport, subjectIsOwnedBy } from "afp-core";

const report = {
  schema_version: "afp/0.2",
  report_id: "afp_01HX...",
  subject_uri: "pkg:npm/eslint@9.2.0",
  goal: "auto-fix lint problems before committing",
  expectation: "--fix corrects the quotes and exits 0",
  observed: "exited 1 without naming the non-fixable rule",
  friction_type: "confusing_interface",
  fault_domain: "tool",
  severity: "degraded",
  timestamp: new Date().toISOString(),
};

validateReport(report); // throws ReportInvalid / SecretDetected if not clean

subjectIsOwnedBy("pkg:npm/eslint@9.2.0", "pkg:npm/eslint"); // true
```

```bash
npm install   # from ts/
npm test      # runs the conformance vectors
npm run build
```

Sinks and routing (the CLI side) live in the Python reference implementation
for now; this package covers the validation core a Reporter or Consumer needs.

The schemas under `schemas/` are vendored copies of the canonical
[`spec/schemas/`](../spec/schemas/); the Python test suite
(`tests/test_spec_sync.py`) fails if they diverge.
