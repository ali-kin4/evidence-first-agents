from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from evidence_first_agents.cli import main
from evidence_first_agents.reports import as_json, as_markdown
from evidence_first_agents.scanner import AgentProjectError, inspect_project

EXAMPLES = Path(__file__).parents[1] / "examples"


def _copy_example(tmp_path: Path, name: str) -> Path:
    destination = tmp_path / name
    shutil.copytree(EXAMPLES / name, destination)
    return destination


def _project(tmp_path: Path, *, contract: str | None = None) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "AGENTS.md").write_text("# Instructions\nStay inside the project.\n")
    if contract is None:
        contract = """
[project]
name = "test-agent"

[policy]
required_instruction_files = ["AGENTS.md"]
"""
    (project / "evidence-first-agents.toml").write_text(contract, encoding="utf-8")
    return project


def _codes(report: dict) -> set[str]:
    return {finding["code"] for finding in report["findings"]}


def test_safe_fixture_is_ready(tmp_path: Path) -> None:
    report = inspect_project(_copy_example(tmp_path, "safe-agent"))
    assert report["decision"] == "ready"
    assert report["summary"] == {
        "instructions": 1,
        "skills": 1,
        "mcp_servers": 2,
        "capabilities": 2,
        "warnings": 0,
        "failures": 0,
        "blocked": 0,
    }


def test_ambiguous_fixture_warns(tmp_path: Path) -> None:
    report = inspect_project(_copy_example(tmp_path, "ambiguous-agent"))
    assert report["decision"] == "warn"
    assert {
        "CONTRACT_MISSING",
        "INSTRUCTION_PRECEDENCE_UNDECLARED",
        "MCP_TRANSPORT_UNSPECIFIED",
    } <= _codes(report)


def test_unsafe_fixture_fails(tmp_path: Path) -> None:
    report = inspect_project(_copy_example(tmp_path, "unsafe-agent"))
    assert report["decision"] == "fail"
    assert {
        "APPROVAL_BOUNDARY_MISSING",
        "EMBEDDED_SECRET",
        "WILDCARD_TOOL_SCOPE",
    } <= _codes(report)


def test_missing_project_raises_clear_error(tmp_path: Path) -> None:
    with pytest.raises(AgentProjectError, match="does not exist"):
        inspect_project(tmp_path / "missing")


def test_malformed_contract_raises_clear_error(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / "evidence-first-agents.toml").write_text("[broken", encoding="utf-8")
    with pytest.raises(AgentProjectError, match="Cannot parse"):
        inspect_project(project)


def test_capabilities_must_be_array(tmp_path: Path) -> None:
    project = _project(tmp_path, contract="capabilities = 4\n")
    with pytest.raises(AgentProjectError, match="array of tables"):
        inspect_project(project)


def test_capability_entries_must_be_tables(tmp_path: Path) -> None:
    project = _project(tmp_path, contract='capabilities = ["bad"]\n')
    with pytest.raises(AgentProjectError, match=r"capabilities\[0\]"):
        inspect_project(project)


def test_required_instruction_missing_is_blocked(tmp_path: Path) -> None:
    project = _project(
        tmp_path,
        contract="""
[policy]
required_instruction_files = ["CLAUDE.md"]
""",
    )
    report = inspect_project(project)
    assert report["decision"] == "blocked"
    assert "REQUIRED_INSTRUCTION_MISSING" in _codes(report)


def test_no_root_instructions_warns(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / "AGENTS.md").unlink()
    (project / "evidence-first-agents.toml").write_text("[project]\nname='empty'\n")
    report = inspect_project(project)
    assert report["decision"] == "warn"
    assert "NO_ROOT_INSTRUCTIONS" in _codes(report)


def test_declared_precedence_resolves_multiple_instruction_warning(tmp_path: Path) -> None:
    project = _project(
        tmp_path,
        contract="""
[policy]
required_instruction_files = ["AGENTS.md"]
instruction_precedence = ["AGENTS.md", "CLAUDE.md"]
""",
    )
    (project / "CLAUDE.md").write_text("# Claude\n")
    report = inspect_project(project)
    assert "INSTRUCTION_PRECEDENCE_UNDECLARED" not in _codes(report)
    assert report["decision"] == "ready"


def test_skill_without_name_fails(tmp_path: Path) -> None:
    project = _project(tmp_path)
    skill = project / "skills" / "one" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\ndescription: Useful work\n---\n")
    report = inspect_project(project)
    assert report["decision"] == "fail"
    assert "SKILL_NAME_MISSING" in _codes(report)


def test_skill_without_description_fails(tmp_path: Path) -> None:
    project = _project(tmp_path)
    skill = project / "skills" / "one" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: useful\n---\n")
    report = inspect_project(project)
    assert "SKILL_DESCRIPTION_MISSING" in _codes(report)


def test_missing_skill_reference_is_blocked(tmp_path: Path) -> None:
    project = _project(tmp_path)
    skill = project / "skills" / "one" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: useful\ndescription: Useful work\n---\n"
        "Read [the guide](references/missing.md).\n"
    )
    report = inspect_project(project)
    assert report["decision"] == "blocked"
    assert "SKILL_REFERENCE_MISSING" in _codes(report)


def test_skill_reference_cannot_escape_project(tmp_path: Path) -> None:
    project = _project(tmp_path)
    skill = project / "SKILL.md"
    skill.write_text(
        "---\nname: useful\ndescription: Useful work\n---\n"
        "Read [outside](../outside.md).\n"
    )
    report = inspect_project(project)
    assert "SKILL_REFERENCE_OUTSIDE_ROOT" in _codes(report)


def test_valid_parent_skill_reference_inside_project_is_allowed(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / "shared.md").write_text("# Shared\n")
    skill = project / "skills" / "one" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: useful\ndescription: Useful work\n---\n"
        "Read [shared](../../shared.md).\n"
    )
    report = inspect_project(project)
    assert "SKILL_REFERENCE_OUTSIDE_ROOT" not in _codes(report)
    assert "SKILL_REFERENCE_MISSING" not in _codes(report)


def test_malformed_mcp_json_is_blocked(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / ".mcp.json").write_text("{broken", encoding="utf-8")
    report = inspect_project(project)
    assert "MCP_CONFIG_UNREADABLE" in _codes(report)
    assert report["decision"] == "blocked"


def test_mcp_config_must_be_object(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / ".mcp.json").write_text("[]", encoding="utf-8")
    report = inspect_project(project)
    assert "MCP_CONFIG_INVALID" in _codes(report)


def test_mcp_server_must_be_object(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / ".mcp.json").write_text('{"mcpServers":{"bad":4}}')
    report = inspect_project(project)
    assert "MCP_SERVER_INVALID" in _codes(report)


def test_stdio_transport_is_inferred_from_command(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / ".mcp.json").write_text(
        '{"mcpServers":{"local":{"command":"python","args":[]}}}'
    )
    report = inspect_project(project)
    assert report["inventory"]["mcp_servers"][0]["transport"] == "stdio"
    assert "MCP_TRANSPORT_UNSPECIFIED" not in _codes(report)


def test_sse_transport_is_inferred_from_url(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / ".mcp.json").write_text(
        '{"mcpServers":{"remote":{"url":"https://example.invalid/sse"}}}'
    )
    report = inspect_project(project)
    assert report["inventory"]["mcp_servers"][0]["transport"] == "sse"


def test_literal_secret_is_not_returned_in_report(tmp_path: Path) -> None:
    project = _project(tmp_path)
    secret = "super-private-value"
    (project / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"remote": {"command": "x", "api_key": secret}}})
    )
    report = inspect_project(project)
    assert "EMBEDDED_SECRET" in _codes(report)
    assert secret not in as_json(report)


def test_environment_secret_reference_is_allowed(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"remote": {"command": "x", "token": "${TOKEN}"}}})
    )
    report = inspect_project(project)
    assert "EMBEDDED_SECRET" not in _codes(report)


def test_missing_capability_source_is_blocked(tmp_path: Path) -> None:
    project = _project(
        tmp_path,
        contract="""
[[capabilities]]
id = "missing"
kind = "external_account_read"
source = "missing.json"
approval = "not-required"
""",
    )
    report = inspect_project(project)
    assert "CAPABILITY_SOURCE_MISSING" in _codes(report)


def test_capability_source_cannot_escape_project(tmp_path: Path) -> None:
    project = _project(
        tmp_path,
        contract="""
[[capabilities]]
id = "escape"
kind = "external_account_read"
source = "../outside.json"
approval = "not-required"
""",
    )
    report = inspect_project(project)
    assert "CAPABILITY_SOURCE_OUTSIDE_ROOT" in _codes(report)


def test_missing_capability_kind_is_blocked(tmp_path: Path) -> None:
    project = _project(
        tmp_path,
        contract="""
[[capabilities]]
id = "unknown"
approval = "required"
""",
    )
    report = inspect_project(project)
    assert "CAPABILITY_KIND_MISSING" in _codes(report)


def test_required_approval_passes_when_declared(tmp_path: Path) -> None:
    project = _project(
        tmp_path,
        contract="""
[policy]
require_explicit_approval_for = ["network_write"]

[[capabilities]]
id = "api-write"
kind = "network_write"
approval = "required"
""",
    )
    report = inspect_project(project)
    assert "APPROVAL_BOUNDARY_MISSING" not in _codes(report)


def test_wildcard_tools_warn(tmp_path: Path) -> None:
    project = _project(
        tmp_path,
        contract="""
[[capabilities]]
id = "broad-reader"
kind = "external_account_read"
approval = "not-required"
tools = ["*"]
""",
    )
    report = inspect_project(project)
    assert report["decision"] == "warn"
    assert "WILDCARD_TOOL_SCOPE" in _codes(report)


def test_json_report_is_deterministic(tmp_path: Path) -> None:
    project = _copy_example(tmp_path, "safe-agent")
    assert as_json(inspect_project(project)) == as_json(inspect_project(project))


def test_markdown_report_is_narrow_about_readiness(tmp_path: Path) -> None:
    markdown = as_markdown(inspect_project(_copy_example(tmp_path, "safe-agent")))
    assert "**Decision:** READY" in markdown
    assert "does not prove that an agent is universally safe" in markdown


def test_cli_ready_returns_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = _copy_example(tmp_path, "safe-agent")
    assert main([str(project)]) == 0
    assert "**Decision:** READY" in capsys.readouterr().out


def test_cli_fail_returns_one(tmp_path: Path) -> None:
    project = _copy_example(tmp_path, "unsafe-agent")
    assert main([str(project)]) == 1


def test_cli_blocked_returns_two(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / "evidence-first-agents.toml").write_text(
        "[policy]\nrequired_instruction_files=['CLAUDE.md']\n"
    )
    assert main([str(project)]) == 2


def test_cli_writes_requested_reports(tmp_path: Path) -> None:
    project = _copy_example(tmp_path, "safe-agent")
    json_out = tmp_path / "reports" / "report.json"
    markdown_out = tmp_path / "reports" / "report.md"
    result = main(
        [
            str(project),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
            "--format",
            "json",
        ]
    )
    assert result == 0
    assert json.loads(json_out.read_text())["decision"] == "ready"
    assert "**Decision:** READY" in markdown_out.read_text()

