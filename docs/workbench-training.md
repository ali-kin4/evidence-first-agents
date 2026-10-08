# Evidence First Agents — 45-minute workshop

**Audience:** technical instructors, software engineers, DevSecOps, responsible AI teams, and managers deploying agentic workflows.

**Prerequisites:** familiarity with ordinary tool/API permissions helps, but no machine-learning or cybersecurity certification is required.

**Objective:** participants can identify a declared authority boundary, interpret deterministic findings, propose a control, demonstrate the difference using a real rescan of a disposable fictional configuration, and name at least one control that still needs runtime validation.

## 0–8 minutes — What can an agent do?

Open `evidence-first-agents --workbench`. Visit **Customer-support automation** in the scenario library.

Ask:
- What is a safe activity for an agent to do automatically? Reading a ticket? Drafting a reply?
- What changes if the agent updates a customer record without confirmation?
- Which tool is explicitly write-capable, and where does the policy say approval is required?

**Check:** learners can state the difference between a declared read operation and a consequential external write, and avoid claiming all tools are inferred by the scanner.

## 8–18 minutes — Interpret evidence fairly

Compare **Bounded research assistant**, **Ambiguous remote assistant**, and **Unbounded publishing agent**.

Explain the four decisions:
- READY: scanned checks have no findings.
- WARN: ambiguity needs investigation.
- FAIL: a declared check failed.
- BLOCKED: some required evidence could not be resolved.

Have learners predict the label before opening each report. Show the authority map and finding explorer. Discuss why "READY" does not mean a prompt injection cannot redirect a tool.

**Check:** learners can say what was *actually scanned* and what remains unknown.

## 18–32 minutes — Test a remediation on real files, without execution

Select **Unbounded publishing agent**, open **Remediation lab**, and choose:
- Replace the demonstration credential with an environment reference.
- Declare approval for external writes.
- Replace wildcard tool permission with one named operation.

Click **Run disposable-copy rescan**.

Discuss:
- Before: the actual fixture FAILs the static checks.
- After: its edited disposable copy is rescanned.
- The report includes what changed and what did not apply.
- The original unsafe sample remains unchanged; the application does not run the agent.

**Check:** ask the learner to explain how to verify that the real runtime enforces human approval, and why editing a TOML declaration is insufficient.

Variation: choose **Ambiguous remote assistant**. Add the project policy, declare instruction precedence and specify MCP transport. Explain the dependency between creating a policy and adding precedence.

## 32–40 minutes — Threat modeling beyond static configuration

Provide this fictional situation:

> A customer-support assistant summarizes an incoming external ticket before offering to update a CRM record. The ticket content is not an instruction source. What independent tests should the team run before enabling customer-record writes?

Suggested answer:
- Enforce human approval at the real tool boundary.
- Check token scope and intended audience.
- Prevent untrusted ticket text from authorizing side effects.
- Validate approval behavior in nested/delegated agents.
- Evaluate retries, concurrency and audit trails.
- Apply a minimal operation allowlist.

Do not conduct an attack on a real service or expose customer data. The scenario is conceptual and safe.

## 40–45 minutes — Evidence and action

Export the report. Have each participant state:
- One verified static finding.
- One practical configuration change.
- One runtime control still unverified.
- One limitation of the scanner.

### Quick quiz

1. Does an approval declaration establish that the runtime blocks writes? **No.**
2. Is a missing MCP transport proof that the endpoint is malicious? **No.**
3. Why is a wildcard permission difficult to review? **It obscures bounded, named authority.**
4. What happens to remediation edits? **They affect only a temporary fictional copy.**
5. Does READY certify security? **No—only the implemented declared checks passed.**

### Instructor assessment rubric

| Criterion | Not demonstrated | Developing | Strong |
|---|---|---|---|
| Authority mapping | Cannot distinguish read/write | Identifies some tools | Correctly identifies source, scope, write and approval |
| Evidence interpretation | Treats heuristic/static signals as proof | Lists unknowns inconsistently | Separates observed, declared and runtime-unverified |
| Remediation | Suggests generic fixes | Changes one configuration with limited rationale | Proposes scoped control and verifies changed scanner finding |
| Safety | Proposes testing on production | Some awareness of boundaries | Uses disposable fixtures and names independent runtime checks |

This is an instructional demonstration, **not** a validated psychometric instrument or certification.
