"""Deterministic inventory and boundary checks for agent-enabled repositories."""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

INSTRUCTION_NAMES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md")
MCP_FILENAMES = (".mcp.json", "mcp.json")
MCP_PATH_SUFFIXES = (".cursor/mcp.json", ".vscode/mcp.json")
REQUIRED_APPROVAL_KINDS = {
    "browser_write",
    "external_account_write",
    "network_write",
}
SECRET_KEY = re.compile(
    r"(?:api[_-]?key|authorization|password|secret|token)$",
    re.IGNORECASE,
)
LOCAL_LINK = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+)\)")
FRONTMATTER_KEY = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*?)\s*$")


class AgentProjectError(ValueError):
    """Raised when a project cannot be inspected safely."""


def _safe_path(root: Path, declared: str | Path) -> Path:
    candidate = (root / declared).resolve()
    if not candidate.is_relative_to(root):
        raise AgentProjectError(f"Declared path escapes the project directory: {declared}")
    return candidate


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _finding(
    code: str,
    severity: str,
    message: str,
    *,
    path: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "message": message,
    }
    if path is not None:
        result["path"] = path
    return result


def _frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return metadata
        match = FRONTMATTER_KEY.match(line)
        if match:
            metadata[match.group(1)] = match.group(2).strip().strip("\"'")
    return {}


def _local_references(text: str) -> list[str]:
    references = []
    for match in LOCAL_LINK.finditer(text):
        reference = match.group(1).strip().strip("<>")
        reference = reference.split("#", 1)[0].strip()
        if reference:
            references.append(reference)
    return sorted(set(references))


def _discover_instructions(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": name,
            "bytes": (root / name).stat().st_size,
        }
        for name in INSTRUCTION_NAMES
        if (root / name).is_file()
    ]


def _discover_skills(
    root: Path,
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    skills = []
    for path in sorted(root.rglob("SKILL.md")):
        if ".git" in path.parts:
            continue
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            findings.append(
                _finding(
                    "SKILL_OUTSIDE_ROOT",
                    "blocked",
                    "A discovered skill resolves outside the project root.",
                    path=str(path),
                )
            )
            continue
        rel_path = _rel(root, resolved)
        text = resolved.read_text(encoding="utf-8")
        metadata = _frontmatter(text)
        references = _local_references(text)
        skill = {
            "path": rel_path,
            "name": metadata.get("name", ""),
            "description": metadata.get("description", ""),
            "references": references,
        }
        skills.append(skill)

        if not skill["name"]:
            findings.append(
                _finding(
                    "SKILL_NAME_MISSING",
                    "failure",
                    "SKILL.md frontmatter must declare a name.",
                    path=rel_path,
                )
            )
        if not skill["description"]:
            findings.append(
                _finding(
                    "SKILL_DESCRIPTION_MISSING",
                    "failure",
                    "SKILL.md frontmatter must declare a description.",
                    path=rel_path,
                )
            )
        for reference in references:
            target = (resolved.parent / reference).resolve()
            if not target.is_relative_to(root):
                findings.append(
                    _finding(
                        "SKILL_REFERENCE_OUTSIDE_ROOT",
                        "blocked",
                        f"Skill reference escapes the project directory: {reference}",
                        path=rel_path,
                    )
                )
            elif not target.exists():
                findings.append(
                    _finding(
                        "SKILL_REFERENCE_MISSING",
                        "blocked",
                        f"Referenced skill resource does not exist: {reference}",
                        path=rel_path,
                    )
                )
    return skills


def _mcp_paths(root: Path) -> list[Path]:
    paths: set[Path] = set()
    for path in root.rglob("*.json"):
        if ".git" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        if path.name in MCP_FILENAMES or rel.endswith(MCP_PATH_SUFFIXES):
            paths.add(path.resolve())
    return sorted(paths)


def _servers_from_config(config: dict[str, Any]) -> dict[str, Any]:
    for key in ("mcpServers", "servers"):
        servers = config.get(key)
        if isinstance(servers, dict):
            return servers
    return {}


def _infer_transport(server: dict[str, Any]) -> str:
    explicit = str(server.get("transport", "")).strip().lower()
    if explicit:
        return explicit.replace("_", "-")
    if server.get("command"):
        return "stdio"
    url = str(server.get("url", "")).strip().lower()
    if url.endswith("/sse") or "/sse?" in url:
        return "sse"
    if url:
        return "unspecified"
    return "unspecified"


def _is_placeholder(value: str) -> bool:
    stripped = value.strip()
    return (
        not stripped
        or stripped.startswith(("$", "env:", "ENV:", "<"))
        or "${" in stripped
        or stripped.upper().startswith(("YOUR_", "REPLACE_", "EXAMPLE_"))
        or stripped in {"...", "***", "redacted", "REDACTED"}
    )


def _embedded_secret_paths(value: Any, prefix: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            if (
                SECRET_KEY.search(str(key))
                and isinstance(child, str)
                and not _is_placeholder(child)
            ):
                yield child_prefix
            else:
                yield from _embedded_secret_paths(child, child_prefix)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _embedded_secret_paths(child, f"{prefix}[{index}]")


def _discover_mcp(
    root: Path,
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    servers: list[dict[str, Any]] = []
    for path in _mcp_paths(root):
        rel_path = _rel(root, path)
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(
                _finding(
                    "MCP_CONFIG_UNREADABLE",
                    "blocked",
                    f"MCP configuration cannot be parsed: {exc}",
                    path=rel_path,
                )
            )
            continue
        if not isinstance(config, dict):
            findings.append(
                _finding(
                    "MCP_CONFIG_INVALID",
                    "blocked",
                    "MCP configuration must contain a JSON object.",
                    path=rel_path,
                )
            )
            continue

        for secret_path in sorted(_embedded_secret_paths(config)):
            findings.append(
                _finding(
                    "EMBEDDED_SECRET",
                    "failure",
                    f"A credential-like field contains a literal value: {secret_path}",
                    path=rel_path,
                )
            )

        for name, raw_server in sorted(_servers_from_config(config).items()):
            if not isinstance(raw_server, dict):
                findings.append(
                    _finding(
                        "MCP_SERVER_INVALID",
                        "blocked",
                        f"MCP server {name!r} must contain an object.",
                        path=rel_path,
                    )
                )
                continue
            transport = _infer_transport(raw_server)
            record = {
                "config_path": rel_path,
                "name": str(name),
                "transport": transport,
                "has_command": bool(raw_server.get("command")),
                "has_url": bool(raw_server.get("url")),
            }
            servers.append(record)
            if transport == "unspecified":
                findings.append(
                    _finding(
                        "MCP_TRANSPORT_UNSPECIFIED",
                        "warning",
                        f"MCP server {name!r} does not declare an unambiguous transport.",
                        path=rel_path,
                    )
                )
    return servers


def _load_contract(root: Path) -> tuple[dict[str, Any], bool]:
    path = root / "evidence-first-agents.toml"
    if not path.is_file():
        return {}, False
    try:
        with path.open("rb") as handle:
            contract = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise AgentProjectError(f"Cannot parse evidence-first-agents.toml: {exc}") from exc
    return contract, True


def _capability_checks(
    root: Path,
    contract: dict[str, Any],
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized = []
    capabilities = contract.get("capabilities", [])
    if not isinstance(capabilities, list):
        raise AgentProjectError("capabilities must be an array of tables")

    policy = contract.get("policy", {})
    required_kinds = {
        str(item)
        for item in policy.get("require_explicit_approval_for", REQUIRED_APPROVAL_KINDS)
    }
    for index, capability in enumerate(capabilities):
        if not isinstance(capability, dict):
            raise AgentProjectError(f"capabilities[{index}] must be a table")
        cap_id = str(capability.get("id", f"capability-{index + 1}")).strip()
        kind = str(capability.get("kind", "")).strip()
        approval = str(capability.get("approval", "unspecified")).strip().lower()
        source = str(capability.get("source", "")).strip()
        tools = sorted(str(item) for item in capability.get("tools", []))
        record = {
            "id": cap_id,
            "kind": kind,
            "approval": approval,
            "source": source,
            "tools": tools,
        }
        normalized.append(record)

        if not kind:
            findings.append(
                _finding(
                    "CAPABILITY_KIND_MISSING",
                    "blocked",
                    f"Capability {cap_id!r} does not declare a kind.",
                )
            )
        if source:
            try:
                source_path = _safe_path(root, source)
            except AgentProjectError:
                findings.append(
                    _finding(
                        "CAPABILITY_SOURCE_OUTSIDE_ROOT",
                        "blocked",
                        f"Capability {cap_id!r} points outside the project.",
                        path=source,
                    )
                )
            else:
                if not source_path.exists():
                    findings.append(
                        _finding(
                            "CAPABILITY_SOURCE_MISSING",
                            "blocked",
                            f"Capability {cap_id!r} references a missing source.",
                            path=source,
                        )
                    )
        if kind in required_kinds and approval != "required":
            findings.append(
                _finding(
                    "APPROVAL_BOUNDARY_MISSING",
                    "failure",
                    f"Capability {cap_id!r} requires an explicit approval boundary.",
                    path=source or None,
                )
            )
        if "*" in tools:
            findings.append(
                _finding(
                    "WILDCARD_TOOL_SCOPE",
                    "warning",
                    f"Capability {cap_id!r} declares wildcard tool access.",
                    path=source or None,
                )
            )
    return sorted(normalized, key=lambda item: item["id"])


def _decision(findings: list[dict[str, Any]]) -> str:
    severities = {finding["severity"] for finding in findings}
    if "blocked" in severities:
        return "blocked"
    if "failure" in severities:
        return "fail"
    if "warning" in severities:
        return "warn"
    return "ready"


def inspect_project(project_path: str | Path) -> dict[str, Any]:
    """Inspect an agent-enabled repository and return a stable report."""

    root = Path(project_path).resolve()
    if not root.is_dir():
        raise AgentProjectError(f"Project directory does not exist: {root}")

    findings: list[dict[str, Any]] = []
    contract, has_contract = _load_contract(root)
    instructions = _discover_instructions(root)
    skills = _discover_skills(root, findings)
    mcp_servers = _discover_mcp(root, findings)

    if not has_contract:
        findings.append(
            _finding(
                "CONTRACT_MISSING",
                "warning",
                "No evidence-first-agents.toml policy contract was found.",
            )
        )

    policy = contract.get("policy", {})
    required_instructions = [
        str(item) for item in policy.get("required_instruction_files", [])
    ]
    present_instructions = {item["path"] for item in instructions}
    for name in sorted(set(required_instructions) - present_instructions):
        findings.append(
            _finding(
                "REQUIRED_INSTRUCTION_MISSING",
                "blocked",
                f"Required instruction file is missing: {name}",
                path=name,
            )
        )

    if not instructions:
        findings.append(
            _finding(
                "NO_ROOT_INSTRUCTIONS",
                "warning",
                "No AGENTS.md, CLAUDE.md, or GEMINI.md file was found at the project root.",
            )
        )
    if len(instructions) > 1 and not policy.get("instruction_precedence"):
        findings.append(
            _finding(
                "INSTRUCTION_PRECEDENCE_UNDECLARED",
                "warning",
                "Multiple root instruction files exist without declared precedence.",
            )
        )

    capabilities = _capability_checks(root, contract, findings)
    findings.sort(
        key=lambda item: (
            item["severity"],
            item["code"],
            item.get("path", ""),
            item["message"],
        )
    )
    decision = _decision(findings)

    return {
        "schema_version": "1.0",
        "project": {
            "name": str(contract.get("project", {}).get("name", root.name)),
            "contract_present": has_contract,
        },
        "decision": decision,
        "inventory": {
            "instructions": instructions,
            "skills": skills,
            "mcp_servers": mcp_servers,
            "capabilities": capabilities,
        },
        "findings": findings,
        "summary": {
            "instructions": len(instructions),
            "skills": len(skills),
            "mcp_servers": len(mcp_servers),
            "capabilities": len(capabilities),
            "warnings": sum(item["severity"] == "warning" for item in findings),
            "failures": sum(item["severity"] == "failure" for item in findings),
            "blocked": sum(item["severity"] == "blocked" for item in findings),
        },
    }
