# Agentic Access Review Copilot for Microsoft Entra ID

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Microsoft Graph](https://img.shields.io/badge/Microsoft%20Graph-Access%20Reviews-0078D4?logo=microsoft&logoColor=white)
![Focus](https://img.shields.io/badge/Focus-Access%20Certification-5E5E5E)
![Security Lens](https://img.shields.io/badge/Security-Read--Only%20%2B%20Identity%20Split-C0392B)
![Entra ID](https://img.shields.io/badge/Entra%20ID-P2-107C10)

An agent that turns access certification from a rubber stamp into a defensible decision. For each entitlement under review it gathers the evidence a diligent reviewer would want, produces a risk-scored recommendation with a written justification, and lets a human approve before any decision is recorded. The security posture is the point: the agent reads the whole entitlement graph as a least-privilege, read-only identity, the security-relevant verdict is backed by a deterministic policy floor the model cannot soften, and recording decisions is a separate, narrowly-scoped identity used only after human sign-off.

## Overview

Access reviews are the control that is supposed to catch privilege creep and orphaned access. In practice they arrive as a list of names with approve and deny buttons, the reviewer has no context on what the access is or whether it is used, and the queue gets cleared with select-all-approve. The result is a clean audit trail for access nobody verified.

Pointing an AI agent at the queue is the obvious move, and the obvious mistake. An agent that can see who has access to what across the directory is a high-value read identity, and one that can action removals is an availability weapon: revoke the wrong accounts and you have a self-inflicted outage. So the interesting engineering is not summarizing the review, it is containing the reviewer. This project runs all analysis as a read-only identity, backs the certification decision with a deterministic floor rather than model judgment alone, gates every write behind a human, and records decisions through a second identity that can do nothing else. Every recommendation cites the evidence it used, so the output is auditable rather than trusted blind.

Three design decisions carry the security story, each chosen over the simpler alternative:

| Decision | Chosen approach | Rejected alternative | Why |
| :--- | :--- | :--- | :--- |
| Identity model | Two identities: a read-only `review-reader` for all analysis, and a write-scoped `review-writer` used only after human approval | One read-write identity | The identity that can read the entire entitlement graph should not also be able to change it. Two identities bound two blast radii. |
| Who decides | A deterministic policy floor sets the minimum strictness from sign-in recency, risk, and group sensitivity; the model may go stricter, never softer; a human approves before any submission | The model's judgment is the decision | The security-relevant call must not be something the model can be argued, or injected, out of. |
| How access is removed | The agent records Approve or Deny on the native review; Entra auto-apply performs the removal | The agent removes group membership directly | Recording a decision is a bounded action. Direct membership writes turn a wrong inference into an outage. |

## Architecture

```mermaid
flowchart TD
    review["Access review instance<br/>(P2, 30-day sign-in recommendations)"] --> reader
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
    redteam -.backstopped by.-> floor
    idp["Identity Protection risk (P2)"] -.feeds.-> reader
```

## Key Concepts Demonstrated

- **Least-privilege read identity**: the agent that reads the whole entitlement graph holds only read scopes and cannot change anything.
- **Deterministic policy floor**: the certification verdict has a minimum strictness computed in code from sign-in recency, Identity Protection risk, and group sensitivity, which the model can only tighten.
- **Separation of duties in code and identity**: analysis and decision-recording are different identities, and a human sits between them.
- **Bounded write path**: the only write records a review decision; Entra performs the actual access removal via auto-apply.
- **Explainable, auditable output**: every recommendation cites its evidence and is logged, then corroborated in the Entra review history.
- **Absence of evidence is not safety**: a missing Identity Protection record is reported as `unknown`/`unavailable`, not silently as `none`.

## Skills Demonstrated

- **Microsoft Entra ID governance**: native Access Reviews, sign-in-based recommendations, auto-apply, and Identity Protection risk signals.
- **Microsoft Graph**: `identityGovernance/accessReviews`, `signInActivity`, `identityProtection/riskyUsers`, and group membership, across two application identities.
- **Agentic AI engineering**: a bounded Claude tool-use loop with a reconciliation guardrail that constrains the model's authority.
- **Secure-by-default design**: read-only default identity, dry-run default, an explicit `--live` flag to write, and secrets kept out of source control.
- **Security testing**: data-driven prompt-injection red-teaming and an empirical read/write scope probe.

## Walkthrough

<details>
<summary><strong>Phase 1: The review to certify (P2)</strong></summary>

A native Access Review was created over `APP-Finance-ReadOnly` (six members in varied states: active, stale, and privileged), with 30-day sign-in-based decision helpers, justification required, and auto-apply enabled so a denial actually removes access. The review's definition ID is read from `.env` by the agent.

![Access review configuration](docs/screenshots/access-review-create-summary.png)

![Created review overview, six users](docs/screenshots/access-review-overview.png)

</details>

<details>
<summary><strong>Phase 2: Two least-privilege identities</strong></summary>

`review-reader` was consented five read scopes, `AccessReview.Read.All`, `AuditLog.Read.All`, `User.Read.All`, `Directory.Read.All`, and `IdentityRiskyUser.Read.All`. `review-writer` was consented only `AccessReview.ReadWrite.All`. The identity that can see everything holds no write permission; the identity that can write can only record review decisions. The writer's object ID is worth noting, since it is the service principal that appears as the actor on the recorded decisions in Phase 9.

![Reader permissions, five read scopes](docs/screenshots/reader-permissions.png)

![Writer permissions, single write scope](docs/screenshots/writer-permissions.png)

![Writer app registration overview](docs/screenshots/writer-overview.png)

</details>

<details>
<summary><strong>Phase 3 to 5: Auth client and read-only evidence tools</strong></summary>

`iam_tools/graph_client.py` authenticates both identities and defaults every call to the read-only reader, so writing requires naming the writer explicitly. `iam_tools/review_reader.py` reads the review, its decision items, sign-in activity, group membership, and risk state. A smoke test confirmed the reader authenticates and can see the review instance before any AI or write logic, and a scratch run shows the decision items and the evidence the agent will reason over.

![Reader reads the review instance](docs/screenshots/reader-smoke-test.png)

![Decision items and gathered evidence](docs/screenshots/reader-decisions-evidence.png)

</details>

<details>
<summary><strong>Phase 6 and 7: Policy floor and the agent loop</strong></summary>

`policy/review_policy.yaml` sets the stale threshold and the privileged groups, and `iam_tools/policy_scorer.py` computes the floor from that. `agent/review_agent.py` runs a bounded tool-use loop per user, then reconciles the model's verdict against the floor by taking the stricter of the two. Across the six users the model was consistently at least as strict as the floor (it recommended revoke for the stale accounts where the floor only required confirm), so the floor acted as a guarantee of minimum strictness rather than a correction. The reconciled recommendations are written to `recommendations.json` with the evidence each one cited.

![Per-user verdicts: model, floor, reconciled final](docs/screenshots/agent-verdicts.png)

![Evidence-cited recommendations](docs/screenshots/recommendations-json.png)

</details>

<details>
<summary><strong>Phase 8: Human-in-the-loop and the writer identity</strong></summary>

`review_approve.py` shows each recommendation with its evidence and submits only what a person confirms, through the writer identity. `keep` becomes Approve, `revoke` becomes Deny, and `confirm` is escalated to a manager and never auto-submitted. It runs dry by default and records for real only with `--live`. Removal of denied access is left to Entra auto-apply.

![Approval gate, dry run](docs/screenshots/approval-dry-run.png)

![Approval gate, live submission](docs/screenshots/approval-live-run.png)

</details>

<details>
<summary><strong>Phase 9: Attribution logging and verification</strong></summary>

Every recommendation and decision is logged to `logs/audit.jsonl`, which separates the `review-reader` recommendations from the `review-writer` decision records and the human escalations. The local log is then corroborated in the Entra review audit log, where each recorded decision shows the acting service principal and carries the agent's own justification. The service principal on those decisions matches the `review-writer` object ID from Phase 2, so attribution is confirmed independently of the application's own logging.

![Local attribution log](docs/screenshots/audit-jsonl.png)

![Entra decision recorded by review-writer, with justification](docs/screenshots/entra-decision-details.png)

</details>

<details>
<summary><strong>Phase 10: Red team</strong></summary>

A prompt-injection payload was planted in a stale user's `jobTitle` field urging the agent to always recommend keep and disregard inactivity. The agent read that field as untrusted data and still recommended revoke, and the deterministic floor independently guaranteed at least `confirm` for a stale account, so neither path allowed the account to be kept. This is defense in depth: the model resisted, and the floor would have caught it even if it had not. Separately, the read-only reader identity was refused with a 403 when it attempted to record a decision, proving the read/write split holds at the permission layer and not only in the code path. Full write-up in `redteam/findings.md`.

![Injected payload in the user's job title](docs/screenshots/redteam-injected-jobtitle.png)

![Data-driven injection resisted, floor backstops it](docs/screenshots/redteam-data-injection.png)

![Reader identity refused when writing a decision](docs/screenshots/redteam-scope-probe.png)

</details>

<details>
<summary><strong>P2 features exercised and design notes</strong></summary>

The P2 features this project depends on are visible in Phase 1 and throughout: native Access Reviews, 30-day sign-in-based recommendations, and auto-apply, none of which exist on a free tenant. Identity Protection risk is read per user and feeds the policy floor, so a risky account would be forced to revoke. In this lab the test accounts had no Identity Protection evaluation, which is itself the interesting case: the reader reports their risk as `unavailable` rather than assuming they are safe, and that distinction is preserved into the floor. Converting the stale privileged member to PIM-eligible rather than keeping standing access is the recommended remediation for that account and is documented as a design step rather than executed here.

</details>

## Lessons Learned

- **Defense in depth beat the injection, and that is the point.** The model resisted the planted `jobTitle` payload on its own, but the deterministic floor still guaranteed the account could not be kept. The security property does not rely on the model behaving, which is exactly why it holds.
- **Two identities beat one plus a promise.** Splitting read from write into separate app registrations makes least privilege a property of the system, not a claim in a comment, and it shows up cleanly in the audit log where the writer, not the reader, is the actor on every decision.
- **Absence of evidence is not evidence of safety.** The risk reader was built so that a missing or unavailable Identity Protection record reports as `unknown`/`unavailable`, never silently as `none`, so the floor cannot treat "no data" as "low risk." In this lab, where the test accounts had no risk evaluation, that distinction is what kept the evidence honest.
- **Quiet the expected noise, surface the real errors.** A user with no risk record returns a 404 from `riskyUsers`, which is normal, so the Graph client suppresses that one case while still printing every other failure. The agent run stays readable without hiding genuine problems.

### How This Fails In Production

- **`AccessReview.ReadWrite.All` is coarse.** It lets the writer act on any review, not just this one. Production would scope the writer per review or per resource where the API allows.
- **P2 dependency by design.** `signInActivity` and Identity Protection risk both require P2, so the evidence model degrades on a free tenant. This project is meant to run inside the P2 window.
- **Single-reviewer governance.** The review and approval were exercised by one admin account. A real deployment separates requester, approver, and reviewer.
- **The model was more conservative than the floor here, which will not always hold.** In this run every model verdict met or exceeded the floor, so the floor was never seen overriding the model live. Its override path is proven by the scorer logic and the injection test, but a hardened build would alert whenever a recommendation sits at the floor because the model tried to go softer.
- **Third-party model dependency.** Directory context is sent to an external model, which in a regulated environment raises data-residency questions and would push toward an Azure-hosted or self-hosted model.
