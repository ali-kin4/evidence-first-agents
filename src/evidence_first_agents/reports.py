"""Stable JSON and human-readable Markdown reports."""

from __future__ import annotations

import json
from typing import Any


def as_json(report: dict[str, Any]) -> str:
    """Serialize a report deterministically."""

    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def as_markdown(report: dict[str, Any]) -> str:
    """Render an inspectable decision report."""

    project = report["project"]
    inventory = report["inventory"]
    summary = report["summary"]
    lines = [
        f"# Agent readiness report - {project['name']}",
        "",
        f"**Decision:** {report['decision'].upper()}",
        "",
        "## Inventory",
        "",
        f"- Root instruction files: {summary['instructions']}",
        f"- Skills: {summary['skills']}",
        f"- MCP servers: {summary['mcp_servers']}",
        f"- Declared capabilities: {summary['capabilities']}",
        "",
        "## Findings",
        "",
    ]
    if not report["findings"]:
        lines.append("- No findings.")
    for finding in report["findings"]:
        location = f" ({finding['path']})" if finding.get("path") else ""
        lines.append(
            f"- **{finding['severity'].upper()} - {finding['code']}**{location}: "
            f"{finding['message']}"
        )

    lines.extend(["", "## Declared capabilities", ""])
    if not inventory["capabilities"]:
        lines.append("- None declared.")
    for capability in inventory["capabilities"]:
        tools = ", ".join(capability["tools"]) or "none"
        source = capability["source"] or "not declared"
        lines.append(
            f"- **{capability['id']}**: kind `{capability['kind'] or 'unknown'}`, "
            f"approval `{capability['approval']}`, tools `{tools}`, source `{source}`"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "READY means the declared checks passed for the files inspected. It does not "
            "prove that an agent is universally safe, correct, or free from prompt injection. "
            "Runtime controls and human judgment remain necessary.",
            "",
        ]
    )
    return "\n".join(lines)

