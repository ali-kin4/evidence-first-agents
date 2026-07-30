# Architecture

## Processing boundary

Evidence First Agents is a static, local scanner:

```text
repository files
      |
      v
safe path resolution
      |
      +--> instruction inventory
      +--> skill metadata and references
      +--> MCP JSON normalization
      +--> declared capability contract
      |
      v
ordered findings
      |
      +--> deterministic JSON
      +--> deterministic Markdown
      +--> exit code
```

The scanner does not execute discovered commands, resolve remote resources, or invoke models.

## Modules

- `scanner.py` owns discovery, normalization, boundary checks, and the decision.
- `reports.py` renders the normalized report without changing its meaning.
- `cli.py` handles paths, output files, and exit codes.

Keeping reports separate from checks makes the JSON contract testable and prevents presentation
logic from changing the decision.

## Determinism

Paths, server names, skills, capabilities, and findings are sorted. Reports contain no timestamps,
hostnames, or absolute project paths. Repeated inspection of unchanged files should produce
byte-identical JSON.

## Extension rule

A new provider adapter must:

1. use a documented, repository-local input;
2. avoid executing or connecting to the declared tool;
3. preserve unknown or ambiguous state as a finding;
4. include safe, ambiguous, and unsafe fixtures;
5. document false-positive and false-negative boundaries.

