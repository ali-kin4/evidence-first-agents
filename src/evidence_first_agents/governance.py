"""Evidence-linked governance explanations without extending static scanner claims.

Rules are educational mappings of existing deterministic finding codes, not
severity CVSS scores or proof of exploitability.
"""
from __future__ import annotations

from typing import Any

REFERENCES = {
    "owasp": {
        "label": "OWASP Top 10 for Agentic Applications (2026)",
        "url": "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/",
    },
    "mcp": {
        "label": "MCP Security Best Practices",
        "url": "https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices",
    },
    "approval": {
        "label": "OpenAI Agents SDK: human-in-the-loop",
        "url": "https://openai.github.io/openai-agents-python/human_in_the_loop/",
    },
    "nist": {
        "label": "NIST AI RMF Generative AI Profile (AI 600-1)",
        "url": "https://doi.org/10.6028/NIST.AI.600-1",
    },
}
# Each entry describes a *visible configuration signal*. The citations provide
# context, not formal certification, nor claims that the specific control was tested.
RULES: dict[str, dict[str, str]] = {
    "EMBEDDED_SECRET": {
        "domain": "Identity & credentials", "reference": "mcp",
        "title": "Literal credential in MCP configuration",
        "why": "A credential-like field contains a literal. Exposure depends on storage and access; this scan does not determine whether the credential is active.",
        "fix": "Remove the literal from the tracked configuration, reference an environment-managed secret, and rotate it if exposed.",
        "verify": "Rescan and separately inspect secret storage, repository history, runtime token audience and scope.",
    },
    "APPROVAL_BOUNDARY_MISSING": {
        "domain": "Human authorization", "reference": "approval",
        "title": "Required approval is not declared",
        "why": "A write capability lacks the approval requirement specified by the local policy. Declaring approval is not proof that a runtime enforces it.",
        "fix": "Declare approval = \"required\" for the affected capability; enforce and test approval at the execution boundary.",
        "verify": "Rescan, then run an authorized test that confirms the tool pauses before side effects, including nested calls.",
    },
    "WILDCARD_TOOL_SCOPE": {
        "domain": "Least privilege", "reference": "owasp",
        "title": "Overly broad declared tool scope",
        "why": "A '*' scope prevents meaningful review of declared operation boundaries. Actual runtime permissions remain unverified.",
        "fix": "Replace '*' with only the named operations the workflow genuinely needs.",
        "verify": "Rescan and test allowlist enforcement with disallowed and allowed tool calls.",
    },
    "MCP_TRANSPORT_UNSPECIFIED": {
        "domain": "MCP connection policy", "reference": "mcp",
        "title": "MCP transport is ambiguous",
        "why": "A remote server URL has no unambiguous declared transport; the scanner cannot infer its security properties.",
        "fix": "Declare the actual supported transport, then review TLS, authorization and server provenance separately.",
        "verify": "Rescan; independently confirm the MCP client/server negotiate the expected transport.",
    },
    "INSTRUCTION_PRECEDENCE_UNDECLARED": {
        "domain": "Instruction provenance", "reference": "owasp",
        "title": "Competing instruction files",
        "why": "More than one root instruction surface exists without declared precedence. This does not prove instruction conflict or prompt injection.",
        "fix": "Document the intended instruction-precedence order and review the instructions for contradictions.",
        "verify": "Rescan; manually verify that the actual agent runtime follows the intended policy.",
    },
    "CONTRACT_MISSING": {
        "domain": "Policy evidence", "reference": "nist",
        "title": "No declared governance contract",
        "why": "The scan cannot compare declared capabilities against an explicit project policy.",
        "fix": "Add an evidence-first-agents.toml contract declaring the intended instructions and approval kinds.",
        "verify": "Rescan and confirm the contract reflects actual runtime authority, not merely aspirational language.",
    },
    "SKILL_REFERENCE_MISSING": {
        "domain": "Agent supply chain", "reference": "owasp",
        "title": "Broken skill reference",
        "why": "The skill references a local resource that cannot be resolved, leaving its intended supporting evidence incomplete.",
        "fix": "Restore the referenced resource or remove the incorrect link after reviewing the skill package.",
        "verify": "Rescan and review the contents of the restored or linked resource.",
    },
    "SKILL_REFERENCE_OUTSIDE_ROOT": {
        "domain": "Agent supply chain", "reference": "owasp",
        "title": "Skill reference escapes project",
        "why": "A skill points outside the inspected project boundary.",
        "fix": "Move the required evidence into the project or explicitly redesign the trust boundary.",
        "verify": "Rescan, and separately review symlinks and runtime file access.",
    },
    "REQUIRED_INSTRUCTION_MISSING": {
        "domain": "Policy evidence", "reference": "nist",
        "title": "Required agent policy missing",
        "why": "A required root instruction file is absent from the selected project.",
        "fix": "Supply the policy-required instruction file and reconcile it with actual agent settings.",
        "verify": "Rescan and confirm the file is loaded by the target runtime.",
    },
    "CAPABILITY_SOURCE_MISSING": {
        "domain": "Evidence traceability", "reference": "nist",
        "title": "Capability evidence missing",
        "why": "The declared capability points to a source that cannot be found.",
        "fix": "Correct its source path or add the missing evidence.",
        "verify": "Rescan and review the provenance of the declared capability.",
    },
    "CAPABILITY_SOURCE_OUTSIDE_ROOT": {
        "domain": "Evidence traceability", "reference": "nist",
        "title": "Capability evidence outside scope",
        "why": "The declared source escapes the scanned project boundary.",
        "fix": "Make the dependency explicit and include inspectable evidence in the review scope.",
        "verify": "Rescan after defining the intended inspection boundary.",
    },
    "NO_ROOT_INSTRUCTIONS": {
        "domain": "Policy evidence", "reference": "nist",
        "title": "No root instruction file",
        "why": "No supported root instruction file was discovered. Other runtime instructions may still exist.",
        "fix": "Document the intended instruction source and match it to the target runtime.",
        "verify": "Rescan; review any unscanned provider-specific sources manually.",
    },
}

DOMAIN_ORDER = (
    "Policy evidence", "Identity & credentials", "Least privilege",
    "Human authorization", "MCP connection policy", "Instruction provenance",
    "Agent supply chain", "Evidence traceability",
)
SCANNER_SCOPE = (
    "Reads selected project files, policy declarations, local skill references and "
    "MCP configuration. Does not execute agents, verify OAuth audience, inspect "
    "MCP server implementations, detect arbitrary prompt injection, or prove "
    "human approval is enforced at runtime."
)


def explain_finding(finding: dict[str, Any], index: int = 0) -> dict[str, Any]:
    """Return curated explanations without emitting source file contents or secrets."""
    code = str(finding["code"])
    meta = RULES.get(code, {})
    ref_key = meta.get("reference", "nist")
    return {
        "id": f"{code}:{index}",
        "code": code,
        "severity": finding["severity"],
        "title": meta.get("title", code.replace("_", " ").title()),
        "domain": meta.get("domain", "Other configuration evidence"),
        "path": finding.get("path"),
        "message": finding["message"],
        "why": meta.get(
            "why", "The deterministic scanner identified a configuration condition that needs review."
        ),
        "fix": meta.get(
            "fix", "Review the finding, correct the local evidence, then rescan."
        ),
        "verify": meta.get(
            "verify", "Rescan; independently verify any runtime enforcement requirement."
        ),
        "reference": REFERENCES[ref_key],
        "evidenceType": "static-configuration-signal",
    }


def governance_view(report: dict[str, Any]) -> dict[str, Any]:
    """Explain static findings and separate observable declarations from runtime gaps."""
    explained = [explain_finding(item, i) for i, item in enumerate(report["findings"])]
    domains = []
    for domain in DOMAIN_ORDER:
        matching = [item for item in explained if item["domain"] == domain]
        domains.append({
            "name": domain,
            "findings": len(matching),
            "state": "attention" if matching else "no-detected-finding",
            "scope": "Checks in this category are partial; no detected finding is not certification.",
        })
    inventory = report["inventory"]
    authority = [
        {
            "id": cap["id"], "kind": cap["kind"], "approval": cap["approval"],
            "source": cap["source"], "tools": cap["tools"],
            "evidence": "project-declared",
            "runtimeVerified": False,
        }
        for cap in inventory["capabilities"]
    ]
    return {
        "decision": report["decision"],
        "project": report["project"]["name"],
        "summary": report["summary"],
        "scope": SCANNER_SCOPE,
        "findings": explained,
        "domains": domains,
        "authority": authority,
        "inventory": inventory,
        "references": REFERENCES,
        "assurance": "static-configuration-review-only",
        "runtimeTested": False,
        "limitations": [
            "No runtime tool calls are made.",
            "Approval declarations do not establish enforcement.",
            "Credential audience, trust, and revocation cannot be checked offline.",
            "Prompt-injection resistance is not measured.",
            "No predictive security score or certification is produced.",
        ],
    }
