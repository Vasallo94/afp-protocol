# AGENTS.md — instructions for coding agents

AFP (Agent Feedback Protocol) is a **protocol spec plus its Python reference
implementation**. The spec under `spec/` is the product; the code exists to
prove the spec works.

## Commands

```bash
uv sync                 # install (Python >= 3.11)
uv run pytest -q        # full test suite — must pass before every commit
uv run afp --help       # the reference CLI
uv build                # wheel + sdist (CI runs this too)
```

## Architecture (read this before touching routing)

- `src/afp/` layers: `models` (the data) → `validate` (redact → secret
  hard-block → JSON Schema → subject_uri) → `discovery` (*decides* which sinks
  the policy allows) → `sinks.route` (*enforces*, incl. anti-spoofing) →
  `sinks.get_sink` (*constructs*). Keep decision/enforcement/construction
  separated.
- `spec/schemas/` is the **canonical** source of the JSON Schemas;
  `src/afp/schema/` is a vendored copy for packaging. Edit the canonical one
  first, then copy — `tests/test_spec_sync.py` fails if they diverge.
- `spec/vectors/` are conformance test vectors and **part of the spec**:
  any behavior change in validation, ownership, or redaction starts by adding
  or changing a vector, then making implementations pass it.
  `tests/test_conformance_vectors.py` is the reference runner.

## Security invariants (never weaken without an explicit decision)

1. **No manifest → no remote sink, ever.** Only `local`/`draft`
   (`discovery.py`). Remote delivery is maintainer opt-in via `afp.json`
   with `accepts_remote: true`.
2. **Ownership check before any remote deposit** (`sinks.subject_is_owned_by`):
   the report's `subject_uri` must fall under the manifest's.
3. **Secret hard-block aborts; email PII redacts and continues**
   (`redact.py`). Order matters and is normative (SPEC §8).
4. **Report content is untrusted** — anything rendered into issues goes
   through `sinks/render.py` sanitization (no `@`/`#` autolinks, no HTML,
   no fence breakout).

## Workflow conventions

- **Strict TDD**: failing test first, minimal implementation after. Security
  findings need adversarial test cases before merging.
- **Atomic commits, directly on `main`**, conventional-commit style
  (`feat(scope):`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`). Bodies may be
  in Spanish; the normative spec and README are English.
- Design docs live in `docs/superpowers/specs/`, implementation plans in
  `docs/superpowers/plans/`, ADRs in `docs/adr/`. Non-trivial protocol
  decisions get an ADR.
- **Dogfooding**: friction found while using AFP itself is reported with
  `uv run afp dogfood ... --sink draft`. The `AFP-REVIEW:` stderr prefix is a
  documented contract — do not change or remove it casually.
