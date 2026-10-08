"""Disposable-copy, actual-rescan policy remediation exercises (no execution)."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from typing import Any

from .demo_cases import SCENARIOS
from .governance import governance_view
from .scanner import inspect_project

CONTROLS = {
    "environment_secret": "Replace literal training credential with an env reference",
    "require_approval": "Declare human approval for write capabilities",
    "limit_tools": "Replace wildcard tool access with named operations",
    "policy_contract": "Create a declared governance policy contract",
    "instruction_precedence": "Declare instruction source priority",
    "mcp_transport": "Set an explicit MCP transport",
}


def _write(root: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def scenario_report(key: str) -> dict[str, Any]:
    if key not in SCENARIOS:
        raise ValueError("Unknown scenario")
    with tempfile.TemporaryDirectory(prefix="efa-case-") as dirname:
        _write(Path(dirname), SCENARIOS[key]["files"])
        report = inspect_project(dirname)
    meta = SCENARIOS[key]
    return {
        "key": key, "synthetic": True, "governance": governance_view(report),
        "report": report,
        "story": {name: meta[name] for name in ("title", "subtitle", "workflow", "lesson")},
    }


def _control(root: Path, control: str) -> bool:
    config = root / "evidence-first-agents.toml"
    mcp = root / ".mcp.json"
    if control == "policy_contract" and not config.exists():
        config.write_text(
            '[project]\nname = "agent-training"\n\n[policy]\n'
            'required_instruction_files = ["CLAUDE.md", "GEMINI.md"]\n',
            encoding="utf-8",
        )
        return True
    if control in {"require_approval", "limit_tools", "instruction_precedence"} and config.exists():
        previous = config.read_text(encoding="utf-8")
        if control == "require_approval":
            new = previous.replace('approval = "none"', 'approval = "required"')
        elif control == "limit_tools":
            new = previous.replace('tools = ["*"]', 'tools = ["issues.comment"]')
        else:
            new = previous.replace(
                'required_instruction_files = ["CLAUDE.md", "GEMINI.md"]',
                'required_instruction_files = ["CLAUDE.md", "GEMINI.md"]\n'
                'instruction_precedence = ["CLAUDE.md", "GEMINI.md"]',
            ) if "instruction_precedence" not in previous else previous
        if new == previous:
            return False
        config.write_text(new, encoding="utf-8")
        return True
    if control in {"environment_secret", "mcp_transport"} and mcp.exists():
        value = json.loads(mcp.read_text(encoding="utf-8"))
        before = copy.deepcopy(value)
        for server in value.get("mcpServers", {}).values():
            if not isinstance(server, dict):
                continue
            if control == "mcp_transport" and server.get("url") and not server.get("transport"):
                server["transport"] = "streamable-http"
            if control == "environment_secret":
                for key in ("headers", "env"):
                    section = server.get(key)
                    if not isinstance(section, dict):
                        continue
                    for name, text in section.items():
                        if name.lower() in ("authorization", "token", "password", "secret"):
                            if isinstance(text, str) and not (
                                text.startswith(("env:", "$")) or "{" in text
                            ):
                                section[name] = "env:DEMO_TOKEN_FROM_ENV"
        if value == before:
            return False
        mcp.write_text(json.dumps(value, indent=2), encoding="utf-8")
        return True
    return False


def simulate(key: str, chosen: list[str]) -> dict[str, Any]:
    if key not in SCENARIOS:
        raise ValueError("Unknown scenario")
    if not isinstance(chosen, list) or len(chosen) > len(CONTROLS):
        raise ValueError("Invalid control selection")
    if any(not isinstance(x, str) or x not in CONTROLS for x in chosen):
        raise ValueError("Unknown control")
    if len(set(chosen)) != len(chosen):
        raise ValueError("Duplicate control")
    before = scenario_report(key)
    with tempfile.TemporaryDirectory(prefix="efa-lab-") as dirname:
        root = Path(dirname)
        _write(root, copy.deepcopy(SCENARIOS[key]["files"]))
        order = (
            "policy_contract", "instruction_precedence", "mcp_transport",
            "environment_secret", "require_approval", "limit_tools",
        )
        applied = [name for name in order if name in chosen and _control(root, name)]
        after_report = inspect_project(root)
    original = {item["code"] for item in before["report"]["findings"]}
    after = {item["code"] for item in after_report["findings"]}
    return {
        "synthetic": True, "scenario": key,
        "method": "rescan-of-disposable-fixture-copy",
        "before": before["governance"],
        "after": governance_view(after_report),
        "requested": chosen,
        "applied": applied,
        "notApplicable": [item for item in chosen if item not in applied],
        "resolved": sorted(original - after),
        "remaining": sorted(after),
        "limitation": (
            "Only fictional files were changed in a disposable directory and rescanned. "
            "Actual runtime permissions, approval enforcement, MCP trust, OAuth and "
            "prompt-injection resistance remain untested."
        ),
    }
