# Red-Team Findings: secure-the-agent

Deliberate tests against the agent identities themselves, treating each as a
privileged non-human identity.

## Threat model

The agent identities (`jml-agent`, `review-reader`, `review-writer`, `nhi-auditor`)
are privileged non-human identities. The realistic threats are: a standing
credential being stolen and replayed with no user and no MFA, the auditor itself
being used to tamper with the identities it inspects, and privilege drift where
an identity holds a scope beyond its declared manifest.

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

**Attempt**: `python -m redteam.over_privilege_probe` had the read-only auditor
try to add a password credential to an application it audits.

**Result**: Blocked at the permission layer with `403 Forbidden`,
`Authorization_RequestDenied: Insufficient privileges to complete the operation`,
on `POST /applications/{id}/addPassword`.

**Stopped by**: Layer 3. The auditor holds only read scopes, so it cannot change
the very identities it inspects.

**Screenshot**: `docs/screenshots/redteam-over-privilege-probe.png`

---

## Finding 2: Real privilege drift (not staged)

**Maps to**: configuration drift, least-privilege enforcement, OWASP NHI risks.

**Attempt**: Run the posture auditor against the declared manifest. This was not a
planted test; it was the first real run.

**Result**: `jml-agent` was flagged CRITICAL for holding `Group.ReadWrite.All`, a
scope not in its manifest. Project 01 had deliberately chosen the narrower
`GroupMember.ReadWrite.All` and flagged `Group.ReadWrite.All` as broader than
needed, but the grant was still live in the tenant. The scope was removed in
Entra and the re-run cleared the CRITICAL, leaving only the standing-secret and
credential-age findings.

**Stopped by**: Layers 1 and 2. The manifest is a live control, so the extra
scope was detected and floored to critical rather than sitting unnoticed.

**Screenshot**: `docs/screenshots/redteam-manifest-drift.png`,
`docs/screenshots/posture-run-clean.png`

---

## Finding 3: Credential-theft blast radius (the case for federation)

**Maps to**: OWASP NHI risks, credential management.

**Attempt**: `python -m redteam.credential_theft <display_name>` against an
identity with a standing secret, and against the federated auditor.

**Result**:
- `jml-agent` (standing secret, not federated): reported RISK, a leaked secret
  grants full agent access with no user and no MFA until it expires.
- `nhi-auditor` (standing secret present and federation configured): reported
  PARTIAL, federation is configured but a standing secret still exists, so the
  benefit is not fully realized until the secret is removed.

**Stopped by**: Layer 3 (federation) once the secret is removed. Residual control
is Conditional Access for workload identities, documented as design (needs
Workload Identities Premium).

**Screenshot**: `docs/screenshots/redteam-credential-theft.png`

---

## Summary

| # | Attack | Outcome | Layer that held |
| :--- | :--- | :--- | :--- |
| 1 | Auditor tries to write a credential | Refused, `403` at the permission layer | Layer 3 |
| 2 | Scope held beyond the manifest (real) | Flagged CRITICAL, then remediated | Layers 1 and 2 |
| 3 | Leaked standing secret | Full access until expiry; federation removes it (PARTIAL until secret deleted) | Layer 3 |

## What would be added in production

- Delete the standing secret entirely once the dev path also moves off secrets.
- Conditional Access for workload identities on each agent service principal
  (needs Workload Identities Premium).
- Continuous posture runs on a schedule via the federated CI identity, alerting
  on any finding at or above HIGH.
- Access reviews / recertification of the service principals themselves (needs
  Workload Identities Premium).
