# Threat model

## Security objective

Make selected repository-local agent configuration easier to inspect without activating the
agent, its tools, or its remote services.

## Assets

- source code and local files;
- credentials referenced by MCP configuration;
- external accounts reachable through tools;
- approval boundaries and tool scopes;
- integrity of the readiness report.

## Considered threats

### Path escape

A skill or capability can reference a path outside the selected repository. Resolved paths are
checked against the project root before existence is evaluated.

### Embedded credentials

MCP JSON can contain literal API keys, tokens, passwords, authorization values, or secrets. The
scanner reports the field path but never includes the value.

### Hidden authority

An external-account, browser, or network write capability can exist without an explicit approval
boundary. The contract makes these capabilities reviewable and fails required approval kinds when
approval is absent.

### Ambiguous transport

A remote MCP URL can be configured without stating whether it uses SSE or Streamable HTTP. The
scanner warns rather than guessing.

### Broken skill package

A skill can advertise a local guide or script that is missing or outside the project. Local
Markdown references are resolved and checked.

## Out of scope

- malicious behavior inside an MCP server, skill script, model, dependency, or shell command;
- runtime prompt injection and data exfiltration;
- symlink races after the scan;
- provider configuration stored outside the repository;
- credentials embedded in arbitrary prose or encoded values;
- proof that a user interface always requests approval;
- formal verification or certification.

## Operational guidance

Run the scanner on a stable checkout. Review every `BLOCKED` and `FAIL` result manually. Treat a
`READY` report as one input to sandboxing, least-privilege configuration, code review, runtime
logging, and human approval—not as a replacement for them.

## Reporting vulnerabilities

Do not publish credentials or private project material. Follow [SECURITY.md](../SECURITY.md).

