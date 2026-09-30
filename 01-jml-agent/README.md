# Agentic Joiner-Mover-Leaver Agent for Microsoft Entra ID

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Microsoft Graph](https://img.shields.io/badge/Microsoft%20Graph-API-0078D4?logo=microsoft&logoColor=white)
![Focus](https://img.shields.io/badge/Focus-IAM%20%2F%20JML%20Lifecycle-5E5E5E)
![Security Lens](https://img.shields.io/badge/Security-Non--Human%20Identity-C0392B)
![Entra ID](https://img.shields.io/badge/Entra%20ID-P2-107C10)
![Status](https://img.shields.io/badge/Status-Complete-2E7D32)

An autonomous agent that reads a plain-language joiner, mover, or leaver ticket, decides which identity actions it implies, and provisions or deprovisions access in Microsoft Entra ID through Microsoft Graph. The differentiator is the security posture around it: the agent is treated as a privileged non-human identity and governed like one, with least-privilege scopes, a policy boundary the model cannot cross, an in-code approval gate for privileged access, full attribution logging, and a documented red-team pass against the agent itself.

## Overview

Joiner-mover-leaver is one of the highest-volume and highest-risk workflows any identity team owns. Done by hand it is slow and inconsistent: movers silently accumulate entitlements they no longer need (privilege creep), and leavers keep orphaned access long after they should, which is exactly the dormant-account and standing-privilege risk that access certification exists to catch. The obvious modern reflex is to point an AI agent at it. The problem is that an agent able to create accounts and grant group membership is itself a superuser, so an agent built without a security instinct simply relocates the risk instead of reducing it.

This project was built around that second point. The provisioning capability is the easy part. The interesting engineering is containment: how the agent's identity was scoped, how a compromised or manipulated agent is prevented from over-granting, how every action is tied back to an accountable human, and what actually happens when the model is fed a hostile ticket. Those questions map directly onto real enterprise controls, so the build is anchored to recognized concepts throughout: least privilege, the JML lifecycle, SOC 2 CC6 logical access and access certification, PIM and zero standing privilege, and, for the agent itself, the OWASP LLM/agentic risk categories and the NIST AI RMF measure-and-manage functions.

Two design decisions define the architecture, both chosen deliberately over the simpler alternative:

| Decision | Chosen approach | Rejected alternative | Why |
| :--- | :--- | :--- | :--- |
| How access is decided | Policy-driven: the model selects a named role, and code resolves that role to a fixed set of groups from `roles.yaml` | Model-decided: let the model name the groups directly | The model can never invent access. Its output is constrained to roles that exist in policy, so a hallucinated or injected group name has nowhere to land. |
| Where the guardrail lives | In code, inside the dispatcher: privileged groups are held for approval regardless of what the model requested | In the system prompt, as an instruction to the model | A prompt is a request, not a control. Enforcing the split in code means the guardrail holds even when the model is wrong or actively manipulated, which was then proven by red-teaming. |
| How entitlements are modeled | Group-based: roles map to security groups, membership is the unit of access | Direct role assignment per user | Group membership is auditable, reviewable, and reversible, and it is the same model access certification and access reviews operate on. |

## Architecture

```mermaid
flowchart TD
    ticket["JML ticket (plain language)<br/>joiner / mover / leaver"] --> agent
    subgraph agent["jml-agent (Claude tool-use loop)"]
        reason["Interpret intent,<br/>choose tools"] --> policy["Policy lookup<br/>roles.yaml"]
        policy --> guard{"Privileged<br/>group?"}
    end
    guard -->|standard access| msgraph["Microsoft Graph<br/>least-privilege app identity"]
    guard -->|privileged access| hold["Held for approval<br/>approvals_pending.json"]
    hold -->|human sign-off via approve.py| pim["PIM eligible<br/>JIT + MFA + justification"]
    pim --> msgraph
    msgraph --> audit["Structured attribution log<br/>audit.jsonl + Entra audit logs"]
    redteam["Red team<br/>prompt injection, scope probe"] -.attacks.-> agent
    redteam -.blocked in code.-> guard
    review["Access reviews (P2)"] -.governs.-> msgraph
    ca["Conditional Access (P2)"] -.protects.-> approver["Human approver"]
```


## Key Concepts Demonstrated

- **Agent as a privileged non-human identity**: the agent authenticates as its own registered application with a scoped, consented permission set, not as a human admin or a shared service account, so its actions are individually attributable and its blast radius is bounded by design.
- **Policy as the trust boundary**: access is expressed as roles in `roles.yaml` and resolved in code, which keeps the language model out of the decision about what a role is allowed to grant.
- **Defense in depth against agent misuse**: three independent layers stand between a malicious instruction and an admin grant, namely the system prompt, the in-code guardrail, and the app's permission scope, and each was tested separately.
- **Zero standing privilege on the riskiest path**: privileged group membership is never granted unattended. It is held for approval, released by a human, and delivered as a PIM-eligible assignment that still requires just-in-time activation with MFA.
- **Attribution and auditability**: every decision and every Graph write is logged locally in structured form and independently confirmed in the Entra audit log as originating from the `jml-agent` identity.
- **Idempotent provisioning**: the agent tolerates duplicate and repeat tickets (rehires, re-runs) rather than failing the batch, which is how real JML pipelines have to behave.

## Skills Demonstrated

- **Microsoft Entra ID administration**: app registrations, application permissions and admin consent, security groups as entitlements, PIM for Groups, access reviews, and Conditional Access.
- **Microsoft Graph automation**: client-credentials authentication with MSAL, and user, group-membership, and audit-log operations against the v1.0 endpoint.
- **Agentic AI engineering**: a Claude tool-use loop with typed tool schemas, a dispatcher, and a bounded reasoning cycle that chains multiple actions from a single natural-language request.
- **Secure-by-default design**: dry-run as the default execution mode, an explicit `--live` flag to write, and secrets kept out of source control.
- **Security testing**: prompt-injection red-teaming, hallucinated-input handling, and an empirical permission-scope probe.
- **Python**: MSAL, Requests, PyYAML, and the Anthropic SDK, organized into a small importable package.

## Repository Layout

This project is the first in a consolidated agentic-AI-in-IAM portfolio and lives under its own folder so later projects can share common plumbing.

```
agentic-ai-iam/
  README.md                     (portfolio index)
  .gitignore
  01-jml-agent/
    README.md                   (this document)
    agent/
      jml_agent.py              (tool schemas, dispatcher, agent loop)
    iam_tools/
      graph_client.py           (auth + Graph wrapper)
      actions.py                (deterministic IAM operations)
    policy/
      roles.yaml                (role-to-group entitlement policy)
    redteam/
      scope_probe.py            (permission-scope test)
      findings.md               (red-team results)
    logs/
      audit.jsonl               (structured attribution log)
      approvals_pending.json    (privileged items awaiting sign-off)
      approvals_completed.json  (released items)
    approve.py                  (human approval workflow)
    tickets.csv                 (simulated JML feed)
    requirements.txt
```

Secrets and generated files (`.env`, `.venv/`, `logs/`, `__pycache__/`) are excluded from source control. A `__pycache__` typo caught during setup was corrected so the ignore rule actually matches.

## Walkthrough

<details>
<summary><strong>Phase 1: Tenant baseline (the entitlement catalog)</strong></summary>

A set of security groups was created to stand in for a role-based access model. Standard entitlements (`APP-Finance-ReadOnly`, `APP-CRM-Standard`, `SHARED-AllStaff`) represent everyday access, and one clearly labeled privileged group (`PRIV-Finance-Admin`) represents access that must never be granted casually. The `PRIV-` naming convention is not cosmetic: it is the signal the policy layer and the guardrail key off to treat that group differently. This group set is the catalog that access certification later reviews against.

![Entra security groups](docs/screenshots/groups.png)

</details>

<details>
<summary><strong>Phase 2: The agent's non-human identity</strong></summary>

The agent authenticates as a dedicated app registration, `jml-agent`, single-tenant, with no interactive sign-in. Its Microsoft Graph application permissions were kept to the minimum the workflow needs and were explicitly admin-consented: `User.ReadWrite.All` to create and disable users, `GroupMember.ReadWrite.All` to manage membership, `AuditLog.Read.All` to read back its own trail, and `Directory.Read.All` for lookups. A short-lived client secret was used for the lab. The most important scoping decision is what the agent was deliberately not given: no directory-role management permission, so it structurally cannot assign an admin role even if instructed to.

![API permissions with admin consent](docs/screenshots/api_permissions.png)

![App registration overview](docs/screenshots/overview_page.png)

</details>

<details>
<summary><strong>Phase 3 and 4: Local environment and model access</strong></summary>

The project runs from an isolated Python virtual environment with its dependencies pinned in `requirements.txt`. Tenant identifiers, the client secret, and the Anthropic API key are loaded from a `.env` file that is excluded from source control. The reasoning model is reached over the Anthropic API as a third-party service, which is called out later as a genuine production consideration for an identity workload.

</details>

<details>
<summary><strong>Phase 5: Graph connectivity</strong></summary>

`graph_client.py` acquires a token with the MSAL client-credentials flow and wraps Graph calls. A read of the first users in the tenant confirmed that the agent identity authenticates and that its permissions resolve before any AI or write logic was added.

![Graph connectivity confirmed](docs/screenshots/terminal_users.png)

</details>

<details>
<summary><strong>Phase 6: Deterministic IAM tools</strong></summary>

All real actions live in `actions.py` as plain, testable functions (`create_user`, `add_to_group`, `disable_user`, `get_group_id`, `find_user`, `get_user_access`). Two properties matter here. First, every write defaults to `dry_run=True`, printing what it would do rather than doing it, so nothing changes until execution is consciously enabled. Second, the model never calls these directly; it only ever requests them through the dispatcher in Phase 8. A dry run and then a real user creation confirmed the tools worked end to end.

![Dry run of a user creation](docs/screenshots/dry_run.png)

![Live user creation returning a real object](docs/screenshots/real_run.png)

**Improvement made during the build**: the first live run failed with an opaque `400 Bad Request` because the Graph wrapper discarded the response body before raising. The wrapper was changed to print Graph's actual error text on failure, which immediately surfaced the real cause and became the pattern for all later debugging.

![The opaque 400 that prompted better error handling](docs/screenshots/error_UPN.png)

</details>

<details>
<summary><strong>Phase 7: Policy-driven entitlements</strong></summary>

`roles.yaml` maps role names to concrete groups and declares which groups are privileged:

```yaml
roles:
  financial_analyst:
    groups: [APP-Finance-ReadOnly, SHARED-AllStaff]
  finance_admin:
    groups: [APP-Finance-ReadOnly, PRIV-Finance-Admin, SHARED-AllStaff]
privileged_groups: [PRIV-Finance-Admin]
```

This file is the trust boundary. The model chooses a role; code turns that role into group IDs and flags anything privileged. Access the policy does not define cannot be granted.

</details>

<details>
<summary><strong>Phase 8: The agentic implementation</strong></summary>

`jml_agent.py` holds three parts: JSON tool schemas that describe the available operations to the model, a dispatcher that maps a requested tool name to its real function, and the tool-use loop itself. The loop calls Claude, runs whatever tool it requests, feeds the result back, and repeats until the model stops requesting tools. This is the agentic behavior: from one plain-language ticket the agent plans and chains multiple steps (for a joiner, create the user, read back the returned ID, then assign role access), deciding each step from the outcome of the last, while every action it can take is one that was defined and gated in code.

A key tool, `assign_role_access`, is policy-aware rather than a raw group operation: the model passes a role, and the dispatcher resolves the entitlements. A dry run showed the agent interpreting a joiner ticket and planning the correct sequence; a live run created the user and assigned exactly the mapped groups.

![Agent planning a joiner in dry run](docs/screenshots/agent_dry_run.png)

![Agent executing a joiner live](docs/screenshots/agent_real_run.png)

</details>

<details>
<summary><strong>Phase 9: Guardrails, human-in-the-loop, and a realistic feed</strong></summary>

Tickets are read from `tickets.csv` to simulate an HR or ticketing feed rather than being hardcoded, and execution mode is controlled by an explicit flag: the agent runs in dry run by default and only writes when invoked with `--live`. This keeps the destructive path behind a conscious action and out of the source file.

![Agent processing a multi-ticket CSV feed in dry run](docs/screenshots/csv-dry-run.png)

The guardrail is enforced inside `assign_role_access`: any group in `privileged_groups` is not executed, it is marked `HELD_FOR_APPROVAL` and written to `approvals_pending.json` with the requester, the group, the target, and a timestamp. Standard access proceeds; privileged access waits. A separate `approve.py` lets a human review and release held items, at which point the grant is executed for real. This models separation of duties: the agent provisions standard access, a person releases privileged access.

![A privileged group held for approval instead of granted](docs/screenshots/held-for-approval.png)

![Human review and release via approve.py](docs/screenshots/approver.png)

**Improvement made during the build**: the first live batch crashed when a ticket referenced a user who already existed, and one failure aborted every remaining ticket. Because rehires and repeated tickets are normal in real JML, `create_user` was made idempotent: on a conflict it detects the existing account, logs a skip, and continues by resolving that user so role reconciliation can still proceed. A leaver ticket for a non-existent user was handled the same way, with the agent reporting the missing account and continuing rather than failing.

![Graceful handling of a duplicate user and a missing leaver](docs/screenshots/graceful_UPN-error.png)

</details>

<details>
<summary><strong>Phase 10: Attribution logging and verification</strong></summary>

Every decision and Graph write is recorded in `audit.jsonl` as a structured line carrying the actor, action, target, result, and whether it was automatic or approved.

![Structured local audit log](docs/screenshots/jsonl.png)

The local log is then corroborated against the source of truth: the Entra audit log shows the user creations and group changes attributed to `jml-agent` as the initiating actor. This is the accountability property the 2026 agent-identity guidance calls for, every agent action traceable to a governed identity, demonstrated independently of the agent's own logging.

![Entra audit log showing jml-agent as the actor](docs/screenshots/entra_audit-logs.png)

</details>

<details>
<summary><strong>Phase 11: Red-teaming the agent</strong></summary>

The agent was attacked to prove the controls hold under hostile input rather than only on the happy path. Results were recorded in `redteam/findings.md`.

**Prompt injection**: several tickets embedded instructions to ignore prior rules and grant `PRIV-Finance-Admin` or Global Administrator. In every case the standard access proceeded and the privileged or admin instruction was refused, both because the guardrail holds privileged groups in code and because no tool to assign a directory role exists to abuse. Multiple phrasings were tried to show the outcome was structural, not a one-off.

![Prompt injection attempt 1](docs/screenshots/prompt_injection_attempt1.png)

![Prompt injection attempt 2](docs/screenshots/prompt_injection_attemp2.png)

![Prompt injection attempt 3](docs/screenshots/prompt_injection_attemp3.png)

**Unknown / hallucinated role**: a ticket for a `super_admin` role that does not exist in policy caused the agent to pause and request explicit confirmation rather than invent an entitlement, and the dispatcher's unknown-role check returns an error so nothing is granted.

![Agent refusing an undefined role](docs/screenshots/hallucination.png)

**Permission-scope probe**: `scope_probe.py` bypassed the agent entirely and hit Graph directly to test the app's true ceiling. The first probe surfaced a nuance worth documenting: the agent could read directory roles and role assignments, because `Directory.Read.All` permits that read.

![Initial scope probe: role management is readable](docs/screenshots/scope-probe.png)

The probe was then sharpened to test the action that actually matters, a role-assignment write, which was blocked at the permission layer. This is the defense-in-depth conclusion: read access exists, but the escalation-enabling write does not, so even a probe that skips every application-level guardrail is stopped by the app's consented scope.

![Refined scope probe: the privileged write is blocked](docs/screenshots/scope-probe-updated.png)

</details>

<details>
<summary><strong>Phase 12: Governance layer (Entra ID P2)</strong></summary>

The automation was wrapped in real identity governance using P2 features.

**PIM for the privileged path**: `PRIV-Finance-Admin` was configured as a PIM-eligible group requiring activation, with Azure MFA, justification, and approval on activation. The agent's approved privileged grant therefore becomes eligibility, not standing access.

![PIM activation settings: MFA, justification, approval](docs/screenshots/member-role-settings.png)

![A PIM-eligible assignment](docs/screenshots/eligible-member.png)

**Access review**: a review over `APP-Finance-ReadOnly` was run end to end, moving from active with pending decisions to complete with recorded approve and deny outcomes, demonstrating the certification cycle the group-based model enables.

![Access review in progress](docs/screenshots/access_review.png)

![Access review completed with decisions applied](docs/screenshots/access-review-decision.png)

**Conditional Access on the human approver**: a policy requiring MFA was created for the approver account, protecting the person who releases privileged access.

![Conditional Access assignment for the approver](docs/screenshots/user_myself.png)

![Conditional Access grant requiring MFA](docs/screenshots/conditiona-policy-require_MFA.png)

</details>

## Lessons Learned

- **A guardrail belongs in code, not in the prompt.** The clearest lesson from red-teaming was that the controls that held under injection were the ones enforced in the dispatcher and in the app's permission scope. Anything left to the system prompt is a request the model can be talked out of. Building the privileged-access split as code, then attacking it, was what turned a claim into evidence.
- **Read the error before reacting to it.** The first live failure was an opaque 400. Surfacing Graph's response body immediately revealed a duplicate-user conflict and made every later issue diagnosable in seconds. Blind `raise_for_status()` hides exactly the information you need.
- **Real provisioning has to be idempotent.** A single pre-existing user aborted the whole batch. Rehires and repeated tickets are normal, so the create path was reworked to detect conflicts and continue. This was the moment the project stopped being a happy-path demo.
- **The trigger and the decision are different things.** The agent's decision-making is automated, but the trigger in this lab is a CSV standing in for an HR or ticketing feed. Being precise about that boundary is more credible than overclaiming autonomy.
- **Redaction is a habit worth showing.** Identifiers were blurred from published screenshots and secrets were never captured, which is both good hygiene and a small signal of the mindset the whole project is about.

### How This Fails In Production

This is a lab, and being explicit about where it ends and production begins is part of the point.

- **Broader permission than needed.** The app was consented `Group.ReadWrite.All`, which is wider than the workflow requires. A production version would tighten to `GroupMember.ReadWrite.All` alone, since the agent only ever changes membership, never group objects. This is a genuine least-privilege refinement I would make next.
- **Conditional Access cannot yet protect the agent's own identity here.** Conditional Access scoped directly to a service principal requires Workload Identities Premium, a separate license not included in P2, so it is documented as a design recommendation rather than implemented: in production the agent's sign-in would be blocked outside known IP ranges and on service-principal risk. The Conditional Access policy in this lab was also left in report-only mode. The first-class direction for this is Microsoft Entra Agent ID, which reached general availability in April 2026 and whose agent-security capabilities require Microsoft 365 Agent or E7 licensing as of July 2026.
- **Secret-based auth.** A client secret is acceptable for a lab but is a credential that can leak. Production would use a certificate or workload identity federation so there is no shared secret at rest.
- **Single-reviewer governance.** The access review and the approval workflow were exercised by one admin account. A real deployment separates the requester, the approver, and the reviewer, which the design supports but the single-tenant lab could not fully demonstrate.
- **Third-party model dependency.** The reasoning model is called over an external API. In a PCI or SOC 2 environment that raises data-residency and data-handling questions about sending identity context off-tenant, and would push toward an Azure-hosted or self-hosted model.
- **No output validation on tool calls.** The guardrail constrains which entitlements can be granted, but a hardened version would also validate the model's tool-call arguments against an allow-list and alert whenever a held item appears, closing the loop from prevention to detection.
