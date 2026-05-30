# AFP Dogfooding Draft Review - 2026-05-30

## Context

First private dogfooding pass for AFP as an out-of-band feedback channel.

Targets:

- `afp-protocol` itself, via `afp dogfood`
- `obsidian-mcp-server`, via repo-level `afp.json` and local draft sink

Policy for this pass:

- No automatic remote issues.
- Drafts are reviewed manually before promotion.
- Public issue candidates must be minimized and redacted.

## Drafts Reviewed

| Target | Subject | Type | Severity | Decision |
| --- | --- | --- | --- | --- |
| AFP | `pkg:pypi/afp@0.2.0` | `confusing_interface` | `cosmetic` | Smoke test only. No action. |
| AFP | `pkg:pypi/afp@0.2.0` | `confusing_interface` | `degraded` | Actioned in `32a18ad`: dogfood enum choices now show in CLI help. |
| Obsidian MCP | `#notes.create` | `confusing_interface` | `degraded` | Candidate issue: result mixes successful creation, validation warning, and full rules dump. |
| Obsidian MCP | `#notes.create` | `confusing_interface` | `degraded` | Candidate issue/doc: clarify vault-relative paths and parent folder behavior. |
| Obsidian MCP | `#notes.patch` | `confusing_interface` | `degraded` | Downgrade after real test: current tool suggests nearby text, so this may already be mostly solved. |
| Obsidian MCP | `#notes.patch` | `wrong_output` | `cosmetic` | Candidate issue: Spanish error text missing accents. |
| Obsidian MCP | `#client.roots` | `integration_mismatch` | `degraded` | Candidate issue/design: make active vault/config easier to confirm from the agent side. |

## Findings

AFP worked for the core thesis: the MCP did not need a new tool, and drafts were created out-of-band in `.afp/drafts`.

The most useful reports were generated after real tool friction, not from speculative examples. The two strongest Obsidian MCP candidates are:

- `notes.create` response shape: success signal gets buried by validation/rules output.
- active vault/config discovery: multi-vault use needs an obvious way to confirm what root is active.

The AFP self-report was immediately useful: `afp dogfood --help` exposed enum discoverability friction, and the fix was small and testable.

## Next Improvements

The manual review loop currently relies on shell tools such as `jq`. That is acceptable for the first pass, but it creates its own friction.

Recommended next AFP feature:

- `afp drafts list --dir <repo>`: summarize local drafts by subject, type, fault domain, severity, and timestamp.
- `afp drafts show <report-id-or-path>`: render a single draft in human-readable form.
- Later, `afp drafts promote <path> --sink github_issues` for explicit human-reviewed promotion.

Do not implement auto-promotion yet.
