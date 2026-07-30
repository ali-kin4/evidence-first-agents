# Roadmap

Evidence First Agents grows by adding checks that are deterministic, explainable, and backed by
realistic fixtures. This roadmap describes candidate work; it is not a promise that every item
will ship unchanged.

## v0.1.1 candidate scope

- Publish a JSON Schema for the report contract and validate example reports against it.
- Add explicit, policy-controlled exclude paths for generated trees, vendored content, and
  deliberately unsafe fixtures.
- Add a repository self-scan workflow once exclusions can be declared without silently hiding
  evidence.
- Improve provider-specific documentation only where a realistic configuration fixture and a
  stable failure mode are available.

## Release gates

A candidate change is release-ready only when:

- its behavior is covered by safe, ambiguous, or unsafe fixtures;
- the same input produces byte-stable JSON and Markdown reports;
- credential values and full instruction contents remain absent from reports;
- lint, tests, packaging, and clean-wheel installation pass on supported platforms;
- documentation states both what the check establishes and what it cannot establish.

## Deliberate non-goals

The roadmap does not include scoring agents with an LLM, executing discovered commands, contacting
configured MCP servers, or claiming that a static report proves runtime safety.

Ideas and reproducible fixtures are welcome in
[GitHub Discussions](https://github.com/ali-kin4/evidence-first-agents/discussions).
