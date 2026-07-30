# Contract reference

## File

The optional policy file is `evidence-first-agents.toml` at the repository root.

Without it, the scanner can still inventory supported files but emits `CONTRACT_MISSING`, so the
highest possible decision is `WARN`.

## Project

```toml
[project]
name = "display-name"
```

## Policy

```toml
[policy]
required_instruction_files = ["AGENTS.md"]
instruction_precedence = ["AGENTS.md", "CLAUDE.md", "GEMINI.md"]
require_explicit_approval_for = [
  "browser_write",
  "external_account_write",
  "network_write",
]
```

`instruction_precedence` records which root instruction surface wins when several providers are
used. Version 0.1 records the declaration; it does not merge instruction semantics.

## Capabilities

```toml
[[capabilities]]
id = "issue-comment"
kind = "external_account_write"
source = ".mcp.json"
approval = "required"
tools = ["issues.comment"]
```

- `id`: stable human-readable identifier.
- `kind`: authority category used by the policy.
- `source`: optional repository-local configuration evidence.
- `approval`: `required`, `not-required`, `none`, or another explicit project value.
- `tools`: bounded operation names. `*` produces a warning.

Default write kinds requiring approval are `browser_write`, `external_account_write`, and
`network_write`.

## Decision precedence

1. Any `blocked` finding produces `BLOCKED`.
2. Otherwise, any `failure` produces `FAIL`.
3. Otherwise, any `warning` produces `WARN`.
4. No findings produces `READY`.

The order prevents missing evidence from being mistaken for a fully evaluated failure.

