"""Fictional agent configuration scenarios for workshops."""
import json

POLICY = (
    '[project]\nname = "agent-training"\n\n[policy]\n'
    'required_instruction_files = ["AGENTS.md"]\n'
    'require_explicit_approval_for = ["external_account_write", "network_write", "browser_write"]\n'
)
SCENARIOS = {
    "safe": {
        "title": "Bounded research assistant",
        "subtitle": "Named tools and declared publishing approval",
        "workflow": "Read an issue, draft a summary, request approval before publishing.",
        "lesson": "READY covers configured static checks, never actual runtime safety.",
        "files": {
            "AGENTS.md": "# Rules\nRequest human approval before external writes.\n",
            ".mcp.json": json.dumps({"mcpServers": {
                "review": {"transport": "streamable-http",
                           "url": "https://example.invalid/mcp",
                           "headers": {"Authorization": "env:DEMO_TOKEN"}},
            }}),
            "evidence-first-agents.toml": POLICY + (
                '\n[[capabilities]]\nid = "read"\nkind = "external_account_read"\n'
                'source = ".mcp.json"\napproval = "not-required"\ntools = ["issues.read"]\n'
                '\n[[capabilities]]\nid = "publish"\nkind = "external_account_write"\n'
                'source = ".mcp.json"\napproval = "required"\ntools = ["issues.comment"]\n'
            ),
        },
    },
    "ambiguous": {
        "title": "Ambiguous remote assistant",
        "subtitle": "Missing precedence, transport and policy",
        "workflow": "Read research material from an MCP source.",
        "lesson": "Missing declarations are not proof of compromise.",
        "files": {
            "CLAUDE.md": "# Policy A\nAnalyze the data.\n",
            "GEMINI.md": "# Policy B\nSummarize the evidence.\n",
            ".mcp.json": json.dumps({"mcpServers": {"remote": {
                "url": "https://example.invalid/mcp",
            }}}),
        },
    },
    "unsafe": {
        "title": "Unbounded publishing agent",
        "subtitle": "Credential literal, wildcard tools and missing approval",
        "workflow": "Publish project updates to an external account.",
        "lesson": "Policy declarations must be validated against real enforcement.",
        "files": {
            "AGENTS.md": "# Instructions\nReview edits before publishing.\n",
            ".mcp.json": json.dumps({"mcpServers": {"publisher": {
                "transport": "streamable-http", "url": "https://example.invalid/mcp",
                "headers": {"Authorization": "FAKE_TRAINING_CREDENTIAL"}},
            }}),
            "evidence-first-agents.toml": POLICY + (
                '\n[[capabilities]]\nid = "publisher"\nkind = "external_account_write"\n'
                'source = ".mcp.json"\napproval = "none"\ntools = ["*"]\n'
            ),
        },
    },
    "business": {
        "title": "Customer-support automation",
        "subtitle": "External CRM update without human approval",
        "workflow": "Read a ticket, draft a reply, update an external CRM record.",
        "lesson": "Read-only assistance and side-effecting actions require distinct controls.",
        "files": {
            "AGENTS.md": "# Support agent\nDraft resolutions carefully.\n",
            ".mcp.json": json.dumps({"mcpServers": {"crm": {
                "transport": "streamable-http", "url": "https://example.invalid/mcp",
                "headers": {"Authorization": "env:DEMO_CRM_TOKEN"},
            }}}),
            "evidence-first-agents.toml": POLICY + (
                '\n[[capabilities]]\nid = "read"\nkind = "external_account_read"\n'
                'source = ".mcp.json"\napproval = "not-required"\ntools = ["tickets.read"]\n'
                '\n[[capabilities]]\nid = "update"\nkind = "external_account_write"\n'
                'source = ".mcp.json"\napproval = "none"\ntools = ["customers.update"]\n'
            ),
        },
    },
}


def catalog():
    return [{"id": key, **{k: value[k] for k in ("title", "subtitle", "workflow", "lesson")}}
            for key, value in SCENARIOS.items()]
