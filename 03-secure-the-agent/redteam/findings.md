# Red-Team Findings: secure-the-agent

Deliberate tests against the agent identities themselves, treating each as a
privileged non-human identity. Fill in results and screenshot references as you
run each probe.

## Threat model

The agent identities (`jml-agent`, `review-reader`, `review-writer`, `nhi-auditor`)
are privileged non-human identities. The realistic threats are: a standing
credential being stolen and replayed with no user and no MFA, the auditor itself
being used to tamper with the identities it inspects, and privilege drift where
an identity quietly gains a scope beyond its declared manifest.

## Defense layers under test

- **Layer 1, the manifest**: a declared least-privilege baseline that the auditor
  grades against. Drift from it is a finding, not a silent change.
- **Layer 2, the deterministic severity floor**: `severity.evaluate` sets the
  minimum severity from the evidence; the model may raise it, never lower it.
- **Layer 3, the credential and identity controls**: workload identity federation
  removes the standing secret, read-only scoping stops the auditor writing, and a
  required owner ties every identity to an accountable human.

---

## Finding 1: Over-privilege scope probe (auditor cannot write)

**Maps to**: verification of least privilege, OWASP Excessive Agency, NIST AI RMF MEASURE.

**Attempt**: `python -m redteam.over_privilege_probe` has the read-only auditor
try to add a password credential to an application it audits.

**Result**: _(expected: blocked at the permission layer, 403 / Authorization_RequestDenied)_

**Stopped by**: Layer 3. The auditor holds only read scopes, so it cannot change
the very identities it inspects.

**Screenshot**: `docs/screenshots/redteam-over-privilege-probe.png`

---

## Finding 2: Credential-theft blast radius (make the case for federation)

**Maps to**: OWASP NHI risks, credential management.

**Attempt**: `python -m redteam.credential_theft <display_name>` before and after
workload identity federation.

**Result**:
- Before (standing secret present): _(record that a leaked secret grants full
  agent access, no user, no MFA, until expiry)_
- After (federated, secret removed): _(record that there is no stored secret to
  steal for the automated path, only a short-lived token)_

**Stopped by**: Layer 3 (federation). Residual control is Conditional Access for
workload identities, documented as design (needs Workload Identities Premium).

**Screenshot**: `docs/screenshots/redteam-credential-theft.png`

---

## Finding 3: Manifest drift (poisoned grant)

**Maps to**: configuration drift, least-privilege enforcement.

**Attempt**: Grant one agent a scope beyond its manifest (for example add
`Group.ReadWrite.All` to `review-reader` and admin-consent it), then run
`python -m auditor.posture_agent`.

**Result**: _(expected: the auditor flags CRITICAL over-privilege drift for that
identity; remove the grant afterward)_

**Stopped by**: Layers 1 and 2. The manifest is a live control, so the extra
scope is detected and floored to critical.

**Screenshot**: `docs/screenshots/redteam-manifest-drift.png`

---

## Summary

| # | Attack | Outcome | Layer that held |
| :--- | :--- | :--- | :--- |
| 1 | Auditor tries to write a credential | _fill in_ | Layer 3 |
| 2 | Leaked standing secret | _fill in_ | Layer 3 (federation) |
| 3 | Scope granted beyond manifest | _fill in_ | Layers 1 and 2 |

## What would be added in production

- Conditional Access for workload identities on each agent service principal
  (needs Workload Identities Premium).
- Continuous posture runs on a schedule via the federated CI identity, with
  alerting on any finding at or above HIGH.
- Access reviews / recertification of the service principals themselves (needs
  Workload Identities Premium).
