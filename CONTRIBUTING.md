# Contributing

Contributions that make agent authority easier to inspect are welcome.

## Development setup

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
evidence-first-agents examples/safe-agent
```

## Pull requests

- Keep changes focused on one documented failure mode.
- Add safe, ambiguous, and unsafe test coverage where applicable.
- Preserve deterministic JSON output.
- Do not execute discovered commands or contact configured services.
- Document false-positive and false-negative boundaries.
- Do not include credentials, personal data, client configuration, or private prompts.

Open an issue before adding a provider adapter or changing the report schema.

