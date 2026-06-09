# AFP: Agent Feedback Protocol

**Specification, version 0.2** · Status: **Draft** · 2026-06-10

Editor: Enrique Vasallo ([@Vasallo94](https://github.com/Vasallo94))

This document is the normative specification of the Agent Feedback Protocol
(AFP). The canonical JSON Schemas live in [`schemas/`](schemas/) and the
conformance test vectors in [`vectors/`](vectors/); where prose and schema
disagree, **the schema wins** for syntactic validity and this document wins for
semantics. A Python reference implementation is maintained in the same
repository under [`src/afp/`](../src/afp/).

---

## 1. Introduction

*This section is non-normative.*

As more of the world's systems are designed for AI agents to operate tools over
them — via MCP, CLIs, skills, HTTP APIs, GUI plugins — there is no standard
channel for those agents to **report the friction they encounter back to the
tool's maintainer**. An agent that hits a bug, an undocumented behavior, or a
missing capability improvises, fails, or tells its user — and the knowledge is
lost.

AFP defines the missing **return path**: a canonical, transport-agnostic way
for an agent to file a *field report* addressed to the tool it used, so the
people (and agents) who maintain that tool learn where, how, and why other
agents failed while using it.

AFP is:

- **A data format first.** The center of the protocol is the field report, not
  the transport. If the report and the tool's identity are well defined, the
  transport and the consumer are interchangeable.
- **Tool-type agnostic.** The protocol does not care whether the subject was an
  MCP server, a CLI, a skill, an HTTP API, or a GUI plugin.
- **Harness agnostic.** It works the same from any agentic environment.
- **Complementary to telemetry.** OpenTelemetry traces *executions*; error
  trackers report *exceptions*. AFP captures **frustrated intent** — what the
  agent wanted, what it expected, and why its plan broke. A field report MAY be
  derived from an OTel trace and linked to it (`trace_id`), but replaces
  neither.

### 1.1 Architecture overview

AFP consists of four separable pieces:

1. **The data** — the Field Report (§4).
2. **The identity** — `subject_uri` and the `afp.json` manifest (§5, §6).
3. **The transport** — sinks (§7, §9).
4. **The loop** — the *Harvester*, a maintainer-side consumer that reads,
   deduplicates, prioritizes, and turns reports into work. The Harvester is
   **not part of this specification**: it is *one* consumer of it, the same way
   a browser is one consumer of HTTP.

## 2. Conventions and terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in [BCP 14](https://www.rfc-editor.org/info/bcp14)
[RFC 2119] [RFC 8174] when, and only when, they appear in all capitals.

- **Field report** — the unit of AFP data: one report of friction encountered
  while using one tool.
- **Subject** — the tool the report is about, identified by `subject_uri`.
- **Manifest** — the `afp.json` file by which a tool's maintainer opts in to
  receiving reports remotely (§6).
- **Sink** — a destination a report can be deposited into (§7).
- **Reporter** — a component that produces field reports (typically an agent or
  its harness).
- **Router** — a component that validates reports and deposits them into sinks
  according to the routing policy (§7). The reference CLI is a Router.
- **Consumer** — a component that reads deposited reports (e.g. a Harvester).

## 3. Conformance

An implementation conforms to this specification as one or more of the
following classes:

- A **Reporter** MUST produce field reports that satisfy §4 and §5.
- A **Router** MUST enforce the validation rules of §4–§5, the routing policy
  of §7, and the redaction rules of §8 before depositing a report into any
  sink. A Router that implements remote sinks MUST enforce ownership
  verification (§7.3) and the rendering requirements of §9.
- A **Consumer** MUST tolerate unknown fields (§4.5) and MUST treat report
  content as untrusted data (§10).

A conforming implementation MUST pass the applicable test vectors in
[`vectors/`](vectors/) (§11).

## 4. The Field Report

### 4.1 Encoding

A field report is a single JSON object (UTF-8). Its syntactic validity is
defined by the canonical JSON Schema
[`schemas/field_report.schema.json`](schemas/field_report.schema.json)
(JSON Schema draft 2020-12).

### 4.2 Core fields (REQUIRED)

A field report MUST contain all of the following fields. Every string field
MUST be non-empty.

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Protocol version, e.g. `afp/0.2`. MUST match `^afp/0\.\d+$` for this major version (§4.5). |
| `report_id` | string | Unique identifier of the report. Reporters SHOULD use a collision-resistant, lexicographically sortable scheme (e.g. ULID with an `afp_` prefix). |
| `subject_uri` | string | Identity of the tool the report is about (§5). |
| `goal` | string | What the agent was trying to achieve, in product language. |
| `expectation` | string | What the agent expected the tool to do or return. |
| `observed` | string | What actually happened. |
| `friction_type` | enum | The kind of friction (§4.4). |
| `fault_domain` | enum | Where the cause appears to lie (§4.4). |
| `severity` | enum | `blocked` \| `degraded` \| `cosmetic`. |
| `timestamp` | string | When it happened (§4.3). |

### 4.3 `timestamp`

The `timestamp` MUST be an [RFC 3339] `date-time`: it MUST include a time
component (`T` separator) and a UTC offset (`Z` or `±HH:MM`). Validators MUST
reject date-only values (`2026-05-30`) and naive datetimes
(`2026-05-30T18:00:00`), which are ambiguous for ordering and grouping.

### 4.4 Closed enumerations

`friction_type` — what kind of friction occurred:

| Value | Meaning |
|-------|---------|
| `bug` | The tool demonstrably misbehaves. |
| `undocumented_behavior` | It works, but in a surprising or undocumented way. |
| `missing_capability` | A capability the plan needed does not exist. |
| `confusing_interface` | The interface or contract induced the error. |
| `wrong_output` | It returned something incorrect or in an unexpected shape. |
| `integration_mismatch` | It fails when combined with the rest of the system. |

`fault_domain` — where the cause *appears* to lie. This is a separate axis
from `friction_type`: not all friction originates in the tool, and a report
stream that distinguishes the tool's own bugs from agent misuse earns the
maintainer's trust. It is a probable domain, not a verdict.

| Value | Meaning |
|-------|---------|
| `tool` | The tool misbehaved. |
| `agent_misuse` | The agent used it incorrectly (malformed input, wrong order). |
| `ambiguous_contract` | The contract was ambiguous; shared fault. |
| `environment_issue` | Network, dependencies, system permissions. |
| `permission_denied` | Missing credentials or permissions. |
| `rate_limit` | Provider throttling. |
| `timeout` | Expired without a response. |

`severity`: `blocked` (the plan could not continue), `degraded` (continued
with loss), `cosmetic` (annoyance without functional impact).

Validators MUST reject values outside these enumerations. The closed
vocabulary is what makes downstream grouping cheap; free text there would make
deduplication an expensive inference problem.

### 4.5 Extension fields, unknown fields, and versioning

All non-core fields are OPTIONAL. This version defines the following extension
fields: `tool_version`, `plan_step`, `workaround`, `inputs_redacted` (object),
`harness`, `harness_version`, `agent_model`, `tool_call_name`, `tool_call_id`,
`trace_id` (OpenTelemetry bridge), `contract_ref`, `evidence` (array),
`confidence` (`high`|`medium`|`low`), `reproducibility`
(`deterministic`|`intermittent`|`once`), and `dedupe_key`. Their semantics
follow the design document; none of them changes routing behavior.

AFP is forward-compatible by design:

- A field report MAY contain fields not defined by this specification.
  Validators MUST NOT reject a report because of an unknown field, and
  implementations that re-emit a report MUST preserve unknown fields intact
  (round-trip integrity). Unknown fields MUST still be subject to the
  redaction and secret rules of §8.
- `schema_version` carries `afp/<major>.<minor>`. An implementation of major
  version 0 MUST accept any minor of major 0 (e.g. `afp/0.99`) and MUST reject
  a different major (e.g. `afp/1.0`).
- An additive change (new optional field) bumps the **minor** version. An
  incompatible change (renaming or removing a core field, changing semantics)
  bumps the **major** version.

## 5. Subject identity (`subject_uri`)

### 5.1 Schemes

The `subject_uri` identifies the tool the report is about. It MUST be
**deterministic**: two different agents, in different harnesses, using the same
tool MUST produce the same URI. AFP reuses existing identifier standards
wherever they exist:

| Tool type | `subject_uri` form | Basis |
|-----------|--------------------|-------|
| Package (CLI/library) | `pkg:npm/eslint@9.2.0`, `pkg:pypi/ruff` | PURL ([ECMA-427]) |
| HTTP API | `https://api.stripe.com/v1/charges` | native URL |
| MCP server | `mcp://github.com/user/repo#tool_name` | MCP-style URI |
| Skill | `afp:skill/namespace/name` | AFP-defined |
| GUI / plugin | `afp:app/platform/plugin` | AFP-defined |
| Opaque binary | `afp:bin/sha256:<hash>` | AFP-defined (last resort) |

Scheme names MUST be lowercase. A `#fragment` names a sub-tool of the subject
(an MCP server's individual tool, a package's sub-command); a PURL `@version`
names a version of it. Neither changes who *owns* the subject (§7.3).

### 5.2 Validation

A Router MUST validate `subject_uri` before depositing:

- The scheme MUST be one of `pkg`, `http`, `https`, `mcp`, `afp`.
- A `pkg:` URI MUST be a syntactically valid PURL.
- For the other schemes the locator part MUST be non-empty.

This version does not further constrain the structure of `http(s)`/`mcp`
locators; they are identifiers first, and §7.3 defines how they are compared.

## 6. The manifest (`afp.json`)

A tool's maintainer opts in to receiving reports by publishing a manifest.
Its syntactic validity is defined by
[`schemas/afp_manifest.schema.json`](schemas/afp_manifest.schema.json).

```json
{
  "afp_version": "0.2",
  "subject_uri": "mcp://github.com/user/nadir-astro",
  "sink": { "type": "github_issues", "repo": "user/nadir-astro", "label": "afp-report" },
  "redaction": "required",
  "accepts_remote": true
}
```

- `afp_version`, `subject_uri`, and `sink` (with at least `sink.type`) are
  REQUIRED. `sink.type` MUST be one of `github_issues`, `gitlab_issues`,
  `local`, `draft`. The `github_issues` and `gitlab_issues` types additionally
  REQUIRE `sink.repo`.
- `accepts_remote` defaults to `false`; `redaction` defaults to `"required"`.
- Unlike field reports, the manifest is **strict**: validators MUST reject a
  manifest with unknown top-level fields. A manifest is the owner's
  configuration, not data in transit between protocol versions; a typo in it
  silently changes routing and must fail loudly.

Routers MUST look for the manifest at `afp.json`, then `.well-known/afp.json`,
relative to the tool's root (repository root, package root, or server base).

## 7. Discovery and routing policy

### 7.1 The golden rule

Sinks are either **local** (`local`, `draft`) or **remote** (`github_issues`,
`gitlab_issues`, and future types like `file`, `http`).

> **Without a manifest declared by the tool, a Router MUST NOT deposit a
> report into any remote sink.** Local sinks are always permitted.

Auto-opening issues on repositories that never asked for them is automated
spam and an abuse vector; remote delivery is always the **maintainer's
opt-in**. Even with a manifest present, remote sinks are permitted only when
the manifest declares `accepts_remote: true`, and only the sink type the
manifest declares.

When no sink is explicitly requested, a Router MUST default to `draft` — the
safe choice, requiring human review before anything leaves the machine.

### 7.2 Sinks

| Type | Behavior | Requires manifest |
|------|----------|-------------------|
| `local` | Appends to a local spool (`.afp/reports.jsonl`). | No |
| `draft` | Writes one file per report under `.afp/drafts/`, keyed by `report_id` (re-deposit overwrites). Intended for explicit human review and promotion. | No |
| `github_issues` | Opens an issue on the declared GitHub repository, labeled (default `afp-report`). | Yes |
| `gitlab_issues` | Opens an issue on the declared GitLab project (self-hosted hosts supported via `sink.host`). | Yes |

### 7.3 Ownership verification (anti-spoofing)

Before depositing into a remote sink, a Router MUST verify that the report's
`subject_uri` **falls under** the manifest's `subject_uri`. This prevents a
forged report from steering content into an unrelated owner's tracker.
Ownership is checked by scheme:

- The schemes MUST be equal, else not owned.
- **`pkg:`** — equal *package base*: strip the `#fragment`, then strip
  `@version`; the remainders MUST be identical. (`pkg:npm/eslint@9.2.0` and
  `pkg:npm/eslint#rule` are both owned by `pkg:npm/eslint`.)
- **`http`, `https`, `mcp`** — the authorities (host[:port]) MUST be equal,
  compared case-insensitively (`api.acme.com.evil.com` is NOT `api.acme.com`;
  an explicit port is a different authority). The report's path, split into
  segments, MUST start with the manifest's path segments: `/v1` owns
  `/v1/charges` but not `/v1abc`; a manifest with no path owns every path on
  its host. Query strings and fragments are ignored.
- **Other schemes** (`afp:`) — equality after stripping the `#fragment`.

An empty subject on either side is never owned.

### 7.4 Delivery semantics

Delivery is **at-least-once**. Remote sinks MUST be idempotent by `report_id`:
a Router MUST keep a local ledger mapping `report_id` to the created reference
(e.g. `.afp/submitted.json` mapping to the issue URL), and a re-deposit of an
already-delivered `report_id` MUST return the prior reference instead of
creating a duplicate. This makes a retry after a network timeout (whose
submission actually landed) safe, without depending on the provider's search
indexing.

Local sinks are not deduplicated: `local` is an append-only spool, and `draft`
already overwrites by `report_id`. *Semantic* deduplication across distinct
reports ("14 agents blocked on the same thing") is the Consumer's job, out of
scope here.

## 8. Data minimization and redaction

Free-text fields (`goal`, `observed`, `workaround`, …) can leak sensitive
data. AFP requires data minimization by default; Reporters SHOULD include the
minimum needed to make the report actionable.

Before any deposit, a Router MUST apply, in this order:

1. **Direct-PII redaction (redact and continue).** Email addresses appearing
   in any string anywhere in the report MUST be replaced with
   `[REDACTED_EMAIL]`. The report then proceeds: an email *mentioned* in free
   text is usually useful context for the maintainer and does not justify
   discarding the report. The email pattern MUST NOT misfire on PURL
   `@version` suffixes (a domain requires a dot-separated TLD).
2. **Secret hard-block (abort).** If any string anywhere in the report —
   including unknown extension fields — matches a high-confidence secret
   pattern, the Router MUST refuse to deposit the report. At minimum,
   implementations MUST detect: OpenAI-style keys (`sk-…`), GitHub PATs
   (`ghp_…`), AWS access key IDs (`AKIA…`), PEM private-key headers, JWTs,
   `Bearer` tokens, Slack tokens (`xox…`), and `key=value`-style secret
   assignments. The pattern list MAY be extended.
3. **Schema validation** (§4) and **subject validation** (§5.2).

This filter is a last line of defense, not a guarantee: phone numbers, names,
and street addresses are not exhaustively detected in this version, and the
Reporter remains responsible for minimization.

## 9. Rendering into remote sinks

Report content is **untrusted data** (§10). When rendering a report into an
issue (or any rich-text surface), a Router MUST neutralize untrusted free-text
fields so they cannot:

- generate platform mentions or cross-references (`@user`, `#123`) — which
  notify third parties before any human reviewed the content;
- inject HTML (`</details>`, `<script>`) or otherwise restructure the body;
- escape code fences (the raw-JSON block MUST be fenced with a backtick run
  strictly longer than any run inside the payload).

The reference rendering escapes `&`, `<`, `>`, and breaks `@`, `#`, and
backtick runs with zero-width spaces. Issue titles SHOULD be of the form
`[AFP/<severity>] <goal>`, with the goal whitespace-collapsed and truncated.

## 10. Security considerations

| Threat | Mitigation (normative) |
|--------|------------------------|
| Automated spam on non-adopting repos | §7.1: no manifest → no remote deposit, ever. Default sink is `draft`. |
| Forged `subject_uri` steering reports to a victim | §7.3 ownership verification against the owner's manifest. |
| Notification abuse / markdown injection via report content | §9 rendering neutralization. |
| Secret exfiltration through reports on public trackers | §8 secret hard-block over every string, including unknown fields. |
| PII leakage in free text | §8 email redaction + minimization; manifest `redaction: "required"`. |
| Prompt injection against LLM Consumers | Consumers MUST treat report content as data, never as instructions (§3). |
| Report poisoning / fake floods | `confidence`, `fault_domain`, closed enums give Consumers cheap signals to weigh, group, and discount; Consumers SHOULD rank, not obey. |

A duplicate-delivery footgun is also closed normatively: §7.4 requires
remote idempotency by `report_id`.

## 11. Test vectors

The files under [`vectors/`](vectors/) are part of this specification:

- `field_report.json` — cases `{description, valid, data}`: report-level
  validation (§4, §5.2), including forward-compatibility and RFC 3339 cases.
- `manifest.json` — cases `{description, valid, data}`: manifest strictness
  (§6).
- `ownership.json` — cases `{description, report_subject, manifest_subject,
  owned}`: the §7.3 algorithm.
- `redaction.json` — cases with `outcome: "secret_block"` (and the
  top-level `offending_fields`) or `outcome: "ok"` (with the `expected`
  post-redaction object): the §8 rules.

A conforming implementation MUST pass every vector applicable to its
conformance class. The reference runner is
[`tests/test_conformance_vectors.py`](../tests/test_conformance_vectors.py).

## 12. Versioning of this specification

This document tracks the `afp/0.x` line. Changes follow §4.5: additive,
backward-compatible changes bump the minor version; incompatible changes bump
the major version and document a migration. The Spanish design document
([`docs/superpowers/specs/2026-05-30-afp-protocol-design.md`](../docs/superpowers/specs/2026-05-30-afp-protocol-design.md))
records the rationale and history that produced this specification; where they
disagree, this document and the schemas win.

---

## Appendix A. Complete example (non-normative)

```json
{
  "schema_version": "afp/0.2",
  "report_id": "afp_01HX8Z2J9Q4R6S8T0V2W4X6Y8Z",
  "subject_uri": "pkg:npm/eslint@9.2.0",
  "goal": "Auto-fix lint problems before committing",
  "expectation": "--fix would correct the quotes and exit 0",
  "observed": "Exited 1 without explaining which rule was not auto-fixable",
  "friction_type": "confusing_interface",
  "fault_domain": "tool",
  "severity": "degraded",
  "timestamp": "2026-05-30T18:00:00Z",
  "plan_step": "3/6 — clean up before tests",
  "workaround": "Parsed stdout by hand",
  "harness": "claude-code",
  "confidence": "high",
  "reproducibility": "deterministic",
  "trace_id": "otel-4bf92f3577b34da6a3ce929d0e0e4736"
}
```

[RFC 2119]: https://www.rfc-editor.org/rfc/rfc2119
[RFC 8174]: https://www.rfc-editor.org/rfc/rfc8174
[RFC 3339]: https://www.rfc-editor.org/rfc/rfc3339
[ECMA-427]: https://ecma-international.org/publications-and-standards/standards/ecma-427/
