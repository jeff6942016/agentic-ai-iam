"""Deterministic policy floor.

The security-relevant decision is computed in code, not by the model. The model
may make a verdict STRICTER than the floor, never softer. That is what defeats
data-driven prompt injection: a stale or risky account cannot be recommended
'keep' no matter what an attacker puts in a directory field.
"""
from datetime import datetime, timezone

import yaml

# Strictness order used to reconcile the model verdict with the policy floor.
RANK = {"keep": 0, "confirm": 1, "revoke": 2}


def load_policy(path="policy/review_policy.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def _days_since(iso):
    if not iso:
        return None
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days


def policy_floor(evidence, policy):
    """Return (verdict, reason): the minimum strictness policy requires."""
    privileged = set(policy.get("privileged_groups", []))
    stale_days = policy["stale_days"]

    risky = evidence["risk"]["riskState"] in ("atRisk", "confirmedCompromised")
    last = evidence["profile"]["lastSignIn"] or evidence["profile"]["lastNonInteractive"]
    days = _days_since(last)
    stale = days is None or days >= stale_days
    is_privileged = bool(privileged.intersection(evidence["groups"]))

    if risky:
        return "revoke", "account is flagged risky by Identity Protection"
    if is_privileged and stale:
        return "revoke", "stale standing access to a privileged group"
    if stale:
        seen = f"{days} days" if days is not None else "no recorded sign-in"
        return "confirm", f"no recent sign-in ({seen}), needs manager confirmation"
    return "keep", f"active account, last sign-in {days} days ago"


def stricter(a, b):
    """Return the stricter of two verdicts."""
    return a if RANK[a] >= RANK[b] else b
