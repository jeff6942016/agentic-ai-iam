# Agentic Access Review Copilot for Microsoft Entra ID

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Microsoft Graph](https://img.shields.io/badge/Microsoft%20Graph-Access%20Reviews-0078D4?logo=microsoft&logoColor=white)
![Focus](https://img.shields.io/badge/Focus-Access%20Certification-5E5E5E)
![Security Lens](https://img.shields.io/badge/Security-Read--Only%20%2B%20Identity%20Split-C0392B)
![Entra ID](https://img.shields.io/badge/Entra%20ID-P2-107C10)

An agent that turns access certification from a rubber stamp into a defensible decision. For each entitlement under review it gathers the evidence a diligent reviewer would want, produces a risk-scored recommendation with a written justification, and lets a human approve before any decision is recorded. The security posture is the point: the agent reads the whole entitlement graph as a least-privilege, read-only identity, the security-relevant verdict is enforced by a deterministic policy floor the model cannot soften, and recording decisions is a separate, narrowly-scoped identity used only after human sign-off.

## Overview

Access reviews are the control that is supposed to catch privilege creep and orphaned access. In practice they arrive as a list of names with approve and deny buttons, the reviewer has no context on what the access is or whether it is used, and the queue gets cleared with select-all-approve. The result is a clean audit trail for access nobody verified.

Pointing an AI agent at the queue is the obvious move, and the obvious mistake. An agent that can see who has access to what across the directory is a high-value read identity, and one that can action removals is an availability weapon: revoke the wrong accounts and you have a self-inflicted outage. So the interesting engineering is not summarizing the review, it is containing the reviewer. This project runs all analysis as a read-only identity, computes the certification decision from deterministic signals rather than model judgment, gates every write behind a human, and records decisions through a second identity that can do nothing else. Every recommendation cites the evidence it used, so the output is auditable rather than trusted blind.

Three design decisions carry the security story, each chosen over the simpler alternative:

| Decision | Chosen approach | Rejected alternative | Why |
| :--- | :--- | :--- | :--- |
| Identity model | Two identities: a read-only `review-reader` for all analysis, and a write-scoped `review-writer` used only after human approval | One read-write identity | The identity that can read the entire entitlement graph should not also be able to change it. Two identities bound two blast radii. |
| Who decides | A deterministic policy floor computes the verdict from sign-in recency, risk, and group sensitivity; the model may go stricter, never softer; a human approves before any submission | The model's judgment is the decision | The security-relevant call must not be something the model can be argued, or injected, out of. |
| How access is removed | The agent records Approve or Deny on the native review; Entra auto-apply performs the removal | The agent removes group membership directly | Recording a decision is a bounded action. Direct membership writes turn a wrong inference into an outage. |

## Architecture

```mermaid
flowchart TD
    review["Access review instance<br/>(P2, with sign-in recommendations)"] --> reader
    subgraph agent["review copilot"]
        reader["review-reader (read-only)<br/>gathers evidence per user"] --> model["Claude tool-use loop<br/>proposes a verdict"]
        model --> floor{"Policy floor<br/>reconcile: model may be stricter, never softer"}
    end
    floor --> recs["recommendations.json<br/>evidence-cited"]
    recs --> human["Human-in-the-loop<br/>review_approve.py"]
    human -->|approved keep / revoke| writer["review-writer (write-scoped)<br/>records decision"]
    human -->|confirm| escalate["Escalated to manager"]
    writer --> entra["Entra auto-apply<br/>removes denied access"]
    writer --> audit["Attribution log<br/>audit.jsonl + Entra review history"]
    redteam["Red team<br/>data injection, scope probe"] -.attacks.-> model
    redteam -.blocked by.-> floor
    idp["Identity Protection risk (P2)"] -.feeds.-> reader
    pim["PIM (P2)"] -.recommends eligible.-> writer
```

## Key Concepts Demonstrated

- **Least-privilege read identity**: the agent that reads the whole entitlement graph holds only read scopes and cannot change anything.
- **Deterministic policy floor**: the certification verdict is computed in code from sign-in recency, Identity Protection risk, and group sensitivity, and the model can only make it stricter.
- **Separation of duties in code and identity**: analysis and decision-recording are different identities, and a human sits between them.
- **Bounded write path**: the only write records a review decision; Entra performs the actual access removal via auto-apply.
- **Explainable, auditable output**: every recommendation cites its evidence and is logged, then corroborated in the Entra review history.
- **Human escalation for ambiguity**: the `confirm` bucket is never auto-submitted, it is escalated to a manager.

## Skills Demonstrated

- **Microsoft Entra ID governance**: native Access Reviews, sign-in-based recommendations, auto-apply, Identity Protection risk, and PIM.
- **Microsoft Graph**: `identityGovernance/accessReviews`, `signInActivity`, `identityProtection/riskyUsers`, and group membership, across two application identities.
- **Agentic AI engineering**: a bounded Claude tool-use loop with a reconciliation guardrail that constrains the model's authority.
- **Secure-by-default design**: read-only default identity, dry-run default, an explicit `--live` flag to write, and secrets kept out of source control.
- **Security testing**: data-driven prompt-injection red-teaming and an empirical read/write scope probe.

## Walkthrough

<details>
<summary><strong>Phase 1: The review to certify (P2)</strong></summary>

Members of `APP-Finance-ReadOnly` were seeded in varied states: active, stale, privileged, and risky. A native Access Review was created over the group with sign-in-based recommendations and auto-apply enabled. Its definition ID is read from `.env`.

![Access review created](docs/screenshots/access-review-created.png)

</details>

<details>
<summary><strong>Phase 2: Two least-privilege identities</strong></summary>

`review-reader` was consented `AccessReview.Read.All`, `AuditLog.Read.All`, `User.Read.All`, `Directory.Read.All`, and `IdentityRiskyUser.Read.All`, all read. `review-writer` was consented only `AccessReview.ReadWrite.All`. The identity that can see everything holds no write permission; the identity that can write can only record review decisions.

![Reader permissions](docs/screenshots/reader-permissions.png)

![Writer permissions](docs/screenshots/writer-permissions.png)

</details>

<details>
<summary><strong>Phase 3 to 5: Auth client and read-only evidence tools</strong></summary>

`iam_tools/graph_client.py` authenticates both identities and defaults every call to the read-only reader, so writing requires naming the writer explicitly. `iam_tools/review_reader.py` reads the review, decision items, sign-in activity, group membership, and risk state. A smoke test confirmed the reader can read the review before any AI or write logic.

![Reader smoke test](docs/screenshots/reader-smoke-test.png)

</details>

<details>
<summary><strong>Phase 6 and 7: Policy floor and the agent loop</strong></summary>

`policy/review_policy.yaml` sets the stale threshold and the privileged groups. `iam_tools/policy_scorer.py` computes the floor from that. `agent/review_agent.py` runs a bounded tool-use loop per user, then reconciles the model's verdict against the floor so the model can only ever be stricter. Runs show a `policy override` wherever the floor made a verdict stricter than the model's.

![Per-user verdicts with a policy override](docs/screenshots/agent-verdicts.png)

</details>

<details>
<summary><strong>Phase 8: Human-in-the-loop and the writer identity</strong></summary>

`review_approve.py` shows each recommendation with its evidence and submits only what a person confirms, through the writer identity. `keep` becomes Approve, `revoke` becomes Deny, and `confirm` is escalated to a manager and never auto-submitted. Removal of denied access is left to Entra auto-apply.

![Approval run](docs/screenshots/approval-run.png)

</details>

<details>
<summary><strong>Phase 9: Attribution logging and verification</strong></summary>

Every recommendation and decision is logged to `logs/audit.jsonl`, then corroborated in the Entra review history, which shows decisions recorded by the `review-writer` identity rather than the reader.

![Local audit log](docs/screenshots/audit-log.png)

![Entra decisions by review-writer](docs/screenshots/entra-decisions.png)

</details>

<details>
<summary><strong>Phase 10: Red team</strong></summary>

A payload placed in a user's `jobTitle` urging the agent to keep access was ignored, and the deterministic floor forced the correct verdict regardless. The read-only reader identity was refused when it tried to record a decision, proving the read/write split holds at the permission layer. See `redteam/findings.md`.

![Data-driven injection held](docs/screenshots/redteam-data-injection.png)

![Reader blocked from writing](docs/screenshots/redteam-scope-probe.png)

</details>

<details>
<summary><strong>Phase 11: Governance layer (P2)</strong></summary>

Identity Protection risk feeds the floor so a risky account is forced to revoke. For the privileged member, the recommendation is to convert standing access to PIM-eligible rather than keep it standing, tying the outcome to zero standing privilege.

![Risky user forced to revoke](docs/screenshots/risky-user-revoke.png)

![PIM-eligible conversion](docs/screenshots/pim-eligible.png)

</details>

## Lessons Learned

- **The certification decision cannot live in the model.** Once the security-relevant verdict is deterministic and the model can only tighten it, prompt injection through directory data stops mattering. The guarantee lives in code.
- **Two identities beat one plus a promise.** Splitting read from write into separate app registrations makes least privilege a property of the system, not a claim in a comment, and it shows up cleanly in the audit log.
- **Recording a decision is safer than removing access.** Letting Entra auto-apply the removals keeps the agent out of direct membership changes, so a wrong call is a wrong review decision, not an outage.

### How This Fails In Production

- **`AccessReview.ReadWrite.All` is coarse.** It lets the writer act on any review, not just this one. Production would scope the writer per review or per resource where the API allows.
- **P2 dependency by design.** `signInActivity` and Identity Protection risk both require P2, so the evidence model degrades on a free tenant. This project is meant to run inside the P2 window.
- **Single-reviewer governance.** The review and approval were exercised by one admin account. A real deployment separates requester, approver, and reviewer.
- **Third-party model dependency.** Directory context is sent to an external model, which in a regulated environment raises data-residency questions and would push toward an Azure-hosted or self-hosted model.
- **Prevention without detection.** The floor prevents bad outcomes but a hardened build would alert whenever a recommendation contradicts the floor (a policy override), surfacing overrides to a SOC rather than only logging them.
