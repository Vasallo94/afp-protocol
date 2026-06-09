# AFP integration block (harness-agnostic)

Embed the block below in any agent runtime's system prompt or rules file —
deep-agent frameworks, custom harnesses, CI agents. It is the same contract as
the Claude Code skill (`../claude-code/afp-report/`), with nothing
Claude-specific in it. Requires the `afp` CLI on PATH
(`uv tool install git+https://github.com/Vasallo94/afp-protocol`).

**The meta case — a harness reporting on itself.** A harness that embeds this
block and publishes its own `afp.json` closes the loop on itself: the LLM
living inside it files field reports *about the harness it is running on*
(`subject_uri: afp:app/<harness>/<component>` or the harness's own
`mcp://...`), and those drafts route back to the harness's maintainers. The
agent becomes the QA of its own cage.

---

```markdown
## Tool friction reporting (AFP)

When a tool you used misbehaves — a bug, undocumented behavior, missing
capability, confusing interface, or wrong output that broke or degraded your
plan — file an AFP field report for the tool's maintainer. Do NOT file for
your own avoidable mistakes or one-off environment flakes. A workaround you
had to invent is a strong signal to file.

1. Determine the deterministic subject_uri:
   packages `pkg:npm/eslint@9.2.0` · MCP tools `mcp://github.com/owner/repo#tool`
   · HTTP APIs `https://api.example.com/v1/x` · skills `afp:skill/ns/name`
   · this harness itself `afp:app/<harness>/<component>`.

2. Write a partial report (JSON) with: subject_uri, goal (what you were
   trying to achieve, product language), expectation, observed,
   friction_type (bug | undocumented_behavior | missing_capability |
   confusing_interface | wrong_output | integration_mismatch),
   fault_domain (tool | agent_misuse | ambiguous_contract |
   environment_issue | permission_denied | rate_limit | timeout — be honest:
   agent_misuse if you misused it),
   severity (blocked | degraded | cosmetic), and optionally workaround,
   harness, tool_call_name. No secrets or personal data in free text.

3. Deposit as a draft (never anything else):
   `afp report --from <partial.json> --submit --dir <tool repo or project root> --sink draft`

4. Relay the `AFP-REVIEW:` stderr line to the human. Promotion to a remote
   sink (real issue) is a HUMAN decision, never yours.

When reviewing existing drafts (`afp drafts list --dir <DIR>`): reproduce the
reported friction against the current tool. If it no longer reproduces, or
its promoted issue is closed, discard with an auditable reason:
`afp drafts discard <id> --dir <DIR> --reason "verified fixed: <evidence>"`.
If it still reproduces, report that to the human instead.
```

---

For the harness's maintainer side, publish an `afp.json` at the harness
repo's root so reviewed drafts can be promoted to your tracker:

```json
{
  "afp_version": "0.2",
  "subject_uri": "afp:app/<harness>/<harness>",
  "sink": { "type": "github_issues", "repo": "<owner>/<repo>", "label": "afp-report" },
  "redaction": "required",
  "accepts_remote": true
}
```
