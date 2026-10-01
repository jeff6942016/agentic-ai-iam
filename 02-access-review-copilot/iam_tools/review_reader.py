"""Read-only evidence tools for an access review.

Everything here runs as the least-privilege 'reader' identity. These are the
facts a diligent human reviewer would gather before deciding on an entitlement:
what the review contains, when the user last signed in, what they belong to,
and whether Identity Protection considers them risky.
"""
from iam_tools.graph_client import graph


def active_instance(definition_id):
    """Return the in-progress review instance (or the most recent one)."""
    out = graph(
        "GET",
        f"/identityGovernance/accessReviews/definitions/{definition_id}"
        f"/instances?$select=id,status,startDateTime,endDateTime",
    )
    values = out.get("value", [])
    for inst in values:
        if inst.get("status") == "InProgress":
            return inst
    return values[0] if values else None


def list_decisions(definition_id, instance_id):
    """Return the decision items (one per user under review)."""
    out = graph(
        "GET",
        f"/identityGovernance/accessReviews/definitions/{definition_id}"
        f"/instances/{instance_id}/decisions"
        f"?$select=id,decision,recommendation,principal,resource,justification",
    )
    return out.get("value", [])


def profile(user_id):
    """User profile plus sign-in activity.

    jobTitle, department and displayName are attacker-influenceable fields and
    are treated as untrusted data by the agent (see redteam/data_injection.py).
    """
    user = graph(
        "GET",
        f"/users/{user_id}"
        f"?$select=displayName,userPrincipalName,jobTitle,department,signInActivity",
    )
    activity = user.get("signInActivity") or {}
    return {
        "displayName": user.get("displayName"),
        "upn": user.get("userPrincipalName"),
        "jobTitle": user.get("jobTitle"),
        "department": user.get("department"),
        "lastSignIn": activity.get("lastSignInDateTime"),
        "lastNonInteractive": activity.get("lastNonInteractiveSignInDateTime"),
    }


def user_groups(user_id):
    """Display names of the groups the user belongs to."""
    out = graph("GET", f"/users/{user_id}/memberOf?$select=id,displayName")
    return [g.get("displayName") for g in out.get("value", []) if g.get("displayName")]


def user_risk(user_id):
    """Identity Protection risk state.

    A clean 404 means Identity Protection has evaluated the user and found no
    risk, which we report as 'none'. Any other failure (an unexpected error, or
    risk data being unavailable) is reported as 'unknown' rather than silently
    treated as safe, so the policy floor never assumes a user is low-risk when
    we actually have no evidence.
    """
    try:
        r = graph("GET", f"/identityProtection/riskyUsers/{user_id}?$select=riskLevel,riskState")
        return {"riskLevel": r.get("riskLevel", "none"), "riskState": r.get("riskState", "none")}
    except Exception as e:
        msg = str(e)
        if "404" in msg and "UnknownError" not in msg:
            return {"riskLevel": "none", "riskState": "none"}
        return {"riskLevel": "unknown", "riskState": "unavailable"}

def gather_evidence(user_id):
    """Convenience: all evidence for one user in one structure."""
    return {
        "profile": profile(user_id),
        "groups": user_groups(user_id),
        "risk": user_risk(user_id),
    }
