---
name: afp-report
description: File an AFP (Agent Feedback Protocol) field report when a tool you used misbehaved — a bug, undocumented behavior, missing capability, confusing interface, or wrong output that broke or degraded your plan. Use after you hit real tool friction (especially if you needed a workaround), or when the user asks to "report this friction", "reporta esta fricción", or "file an AFP report". Reports land as local drafts for human review; nothing is sent anywhere automatically.
---

# Filing an AFP field report

AFP captures **frustrated intent**: what you were trying to do, what you
expected the tool to do, and what actually happened. It is for the tool's
*maintainer*, written in product language — not a stack trace dump.

## When to file

File when friction in a tool **broke or degraded your plan** and the
maintainer could act on it. Do NOT file for your own mistakes (wrong
arguments you could have known), one-off environment flakes, or trivia.
If you found a workaround, that is a *strong* signal to file — the
workaround often suggests the fix.

## How

1. **Determine the `subject_uri`** (must be deterministic):

   | Tool kind | subject_uri |
   |-----------|-------------|
   | CLI / library / package | `pkg:npm/eslint@9.2.0`, `pkg:pypi/ruff` (PURL) |
   | MCP server (tool) | `mcp://github.com/owner/repo#tool_name` |
   | HTTP API | `https://api.example.com/v1/endpoint` |
   | Agent skill | `afp:skill/namespace/skill-name` |

2. **Write the partial report** to a temp file, e.g. `/tmp/afp-partial.json`:

   ```json
   {
     "subject_uri": "pkg:pypi/ruff",
     "goal": "what you were trying to achieve, in product language",
     "expectation": "what you expected the tool to do",
     "observed": "what actually happened",
     "friction_type": "wrong_output",
     "fault_domain": "tool",
     "severity": "degraded",
     "workaround": "how you got around it (omit if none)",
     "harness": "claude-code",
     "tool_call_name": "the exact command/tool you invoked"
   }
   ```

   Closed enums — pick exactly one of each:
   - `friction_type`: `bug` | `undocumented_behavior` | `missing_capability` |
     `confusing_interface` | `wrong_output` | `integration_mismatch`
   - `fault_domain` (where the cause *appears* to lie — be honest, use
     `agent_misuse` if you misused it and the docs could have prevented it):
     `tool` | `agent_misuse` | `ambiguous_contract` | `environment_issue` |
     `permission_denied` | `rate_limit` | `timeout`
   - `severity`: `blocked` | `degraded` | `cosmetic`

   **Minimize data**: no secrets, no tokens, no personal data in free text.
   (The CLI hard-blocks secrets and redacts emails, but write clean first.)

3. **Build and deposit as a draft**:

   ```bash
   afp report --from /tmp/afp-partial.json --submit --dir <DIR> --sink draft
   ```

   `<DIR>`: the tool's local repo if you have it checked out (so a later
   promotion can use its `afp.json`), otherwise the current project root.

   If `afp` is not installed:
   `uv tool install git+https://github.com/Vasallo94/afp-protocol`

4. **Relay the review notice.** The CLI prints `AFP-REVIEW: N drafts ...` on
   stderr. Tell the user, including the exact review command. Drafts are
   reviewed and promoted by a HUMAN (`afp drafts list/show/promote`) — never
   promote to a remote sink yourself.

## The golden rule

Always `--sink draft`. AFP never auto-submits to third parties: remote
delivery is the maintainer's opt-in (their `afp.json`) and the human's
explicit promotion. Your job ends at the draft.
