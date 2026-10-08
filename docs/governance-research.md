# Research and design rationale — Authority Workbench (October 2026)

## Why the project goes beyond a list of red flags

Agentic AI introduces operational consequences: tools may read confidential records, mutate data, send messages, execute commands, and change accounts. Static code inspection alone cannot decide what an agent *will* do in response to an untrusted document or whether a declared approval boundary exists in the actual runtime. A useful governance tool must therefore separate **observed configuration**, **declared intent**, **hypothetical risk** and **verified runtime behavior**.

Evidence First Agents does the first two, and explicitly asks for independent tests of the other two. The workbench is designed to teach a disciplined sequence:

1. Inventory the surfaces and capabilities that can be inspected locally.
2. Identify missing declarations or deterministic contract violations.
3. Map each finding to a plausible consequence and an actionable mitigation.
4. Try the mitigation on a disposable copy of a **fictional** project.
5. Rerun the exact original scanner; inspect changed findings and unresolved unknowns.
6. Define separate runtime validation before any sensitive deployment.

This approach is more useful than a synthetic "security score": a score could imply empirical calibration, exploitability measurement, or governance certification that the scanner does not provide.

## Source-guided design choices

| Primary reference | Relevant guidance | Implemented scope | Important limitation |
|---|---|---|---|
| [OWASP Agentic Top 10 (2026)](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | Agent goal hijack, tool misuse, identity/privilege abuse, supply-chain risks | Organize authority, instructions, tools, skills and policy findings | We do **not** claim coverage or detection of all OWASP categories |
| [MCP Security Best Practices](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/docs/2026-07-28/tutorials/security/security_best_practices.mdx) | Authorization boundaries, token audience, confused deputy and token-passthrough risks | Flag selected MCP configuration ambiguities and literal credential-like values | We cannot establish token audience, scope or actual server trust without runtime checks |
| [OpenAI Agents SDK — Human-in-the-loop](https://openai.github.io/openai-agents-python/human_in_the_loop/) | Pause sensitive tool calls for human approval, including nested tool execution | Make declared approval requirements visible and explain runtime verification | A TOML approval declaration is **not** proof of SDK interruption enforcement |
| [NIST AI 600-1 — GenAI profile](https://doi.org/10.6028/NIST.AI.600-1) | Govern, map, measure and manage AI risks throughout lifecycle | Provide reproducible evidence, scoped assessment language and explicit uncertainty | No formal conformity assessment, external audit or regulatory advice |
| [MITRE ATLAS — agent tool exfiltration](https://d3fend.mitre.org/offensive-technique/attack/AML.T0086/) | Legitimate write tools can be redirected to leak or change information | Teach difference between read and side-effecting tools | We do not run adversarial prompt-injection experiments or prove exploitability |

The mappings are interpretive educational cross-references rather than an official OWASP, MCP, MITRE, NIST, or OpenAI certification.

## Research-derived product opportunities

**Now implemented**
- **Authority pathway map:** source/configuration/capability inventory, explicitly labelled declarations.
- **Evidence-led finding explorer:** why, fix, how to verify and authoritative documentation.
- **Disposable control workbench:** real scanner reruns after synthetic file edits.
- **Workflow-based learning:** safe, ambiguous, unsafe, and customer-support scenarios.
- **Facilitated training:** 45-minute walkthrough suitable for engineering and governance discussions.
- **No false precision:** no arbitrary AI-generated security scores or claims of detection beyond the code's actual rules.

**Future high-value research directions (not implemented)**
1. **Runtime approval proof:** run authorized, isolated benign side-effect tests against specific supported SDKs, including nested delegation and replay controls.
2. **MCP authorization verification:** test token resource audience, passthrough rejection, transport semantics and tool discovery against deliberately instrumented mock servers.
3. **Agent authority diff CI:** compare current and proposed manifests, require human sign-off for increases in scopes and side-effecting capabilities.
4. **Untrusted-content boundary evaluation:** opt-in, sandboxed, harmless prompt-injection test suites with explicit false-positive and false-negative measurement.
5. **Control provenance:** generate attestations binding a reported outcome to commit SHA, tool version, policy contract, and local evidence hashes without leaking secrets.
6. **Policy-as-code interoperability:** map selected checks to OPA/Rego and maintain live fixtures rather than auto-claiming compatibility.
7. **Supply-chain provenance:** verify declared skills and MCP server artifacts using independent signatures/hashes and allowlisted update policies.

These can support applied research and real user studies, but need separate threat modeling, validation datasets and product-security assessment.

## Reviewer interpretation: observation vs assurance

| Output | What it means | What it never proves |
|---|---|---|
| READY | No findings among the implemented declared checks for scanned evidence | Operational safety or trusted remote services |
| WARN | Config ambiguity or warning-level finding | Exploit or real compromise |
| FAIL | A declared contract violation was found | Exploitability or active adversary |
| BLOCKED | Some required evidence was unresolvable | Full evaluation of remaining sources |
| Simulated READY | A disposable **synthetic** copy passed after controls were applied | Production patch deployed, approval actually enforced or all risk gone |

## Safe boundaries and privacy

- No browser-supplied filesystem paths are accepted; scenario names and remediation controls are allowlisted.
- The web server only binds to `127.0.0.1` and serves known assets.
- Temporary workspaces are removed after each scan; original example fixtures are never modified.
- The scanner does not execute local MCP commands, retrieve remote documents or invoke an LLM.
- Fictional credentials and reserved hostnames are used in teaching data.
- Browser export contains sanitized report findings, not raw MCP authorization values.
- There is no user authentication or multi-tenant data model; hosting publicly would require a separate architecture.

## Verification targets

Run the scanner's existing test suite on its supported platforms, add scenario and localhost API tests, build and install the wheel, and complete Chromium desktop/mobile acceptance. Publish screenshots only after they were actually rendered by a browser. Any release claims must correspond to a successful current-commit run.
