# AFP specification

This directory is the **canonical source** of the Agent Feedback Protocol:

- [`SPEC.md`](SPEC.md) — the normative specification (RFC 2119 language).
- [`schemas/`](schemas/) — the canonical JSON Schemas (draft 2020-12) for the
  field report and the `afp.json` manifest. The copy under `src/afp/schema/`
  is vendored for packaging; `tests/test_spec_sync.py` keeps them identical.
- [`vectors/`](vectors/) — language-agnostic conformance test vectors. Any AFP
  implementation, in any language, should pass them.

## Writing an implementation against the vectors

Each vector file is a JSON array of cases with a human-readable `description`
(use it as the test id):

| File | Case shape | What to assert |
|------|-----------|----------------|
| `field_report.json` | `{description, valid, data}` | Full report validation (schema + strict RFC 3339 `timestamp` + `subject_uri` rules) accepts iff `valid`. |
| `manifest.json` | `{description, valid, data}` | Manifest validation (schema + `subject_uri` rules) accepts iff `valid`. |
| `ownership.json` | `{description, report_subject, manifest_subject, owned}` | The §7.3 ownership check returns `owned`. |
| `redaction.json` | `{outcome: "secret_block", data, offending_fields}` | Secret scan reports exactly those top-level fields. |
| | `{outcome: "ok", data, expected}` | No secrets detected, and email redaction of `data` yields `expected`. |

The reference runner is
[`tests/test_conformance_vectors.py`](../tests/test_conformance_vectors.py)
(~30 lines of pytest); porting it is the fastest way to bootstrap a new
implementation.

Vectors are part of the spec: adding behavior to the protocol means adding
vectors here first.
