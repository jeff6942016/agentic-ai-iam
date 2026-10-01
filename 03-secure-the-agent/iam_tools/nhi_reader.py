"""Read-only evidence tools for non-human identity (NHI) posture.

For a given agent identity (an app registration) these gather the facts a
security reviewer needs: what application permissions it actually holds, how it
authenticates (standing secret, certificate, or federated), when those
credentials expire, who owns it, and whether Identity Protection considers its
service principal risky.
"""
from iam_tools.graph_client import graph

# Microsoft Graph's own service principal appId, used to resolve appRole GUIDs
# (the values in appRoleAssignments) back to names like "User.ReadWrite.All".
GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"

_role_map_cache = None


def _graph_role_map():
    """Build a one-time {appRoleId: value} map from Microsoft Graph's app roles."""
    global _role_map_cache
    if _role_map_cache is None:
        sp = graph("GET", f"/servicePrincipals?$filter=appId eq '{GRAPH_APP_ID}'&$select=id,appRoles")
        roles = sp.get("value", [{}])[0].get("appRoles", [])
        _role_map_cache = {r["id"]: r["value"] for r in roles}
    return _role_map_cache


def find_app(display_name):
    out = graph(
        "GET",
        f"/applications?$filter=displayName eq '{display_name}'"
        f"&$select=id,appId,displayName,passwordCredentials,keyCredentials",
    )
    vals = out.get("value", [])
    return vals[0] if vals else None


def find_sp(app_id):
    out = graph("GET", f"/servicePrincipals?$filter=appId eq '{app_id}'&$select=id,appId,displayName")
    vals = out.get("value", [])
    return vals[0] if vals else None


def resolve_roles(assignments):
    """Turn appRoleAssignments (GUIDs) into readable scope names where possible."""
    role_map = _graph_role_map()
    names = []
    for a in assignments:
        rid = a.get("appRoleId")
        names.append(role_map.get(rid, rid))  # fall back to the GUID if unresolved
    return names


def granted_app_roles(sp_id):
    out = graph(
        "GET",
        f"/servicePrincipals/{sp_id}/appRoleAssignments?$select=appRoleId,resourceId,resourceDisplayName",
    )
    return out.get("value", [])


def federated_credentials(app_object_id):
    out = graph("GET", f"/applications/{app_object_id}/federatedIdentityCredentials")
    return out.get("value", [])


def owners(app_object_id):
    out = graph("GET", f"/applications/{app_object_id}/owners?$select=id,userPrincipalName,displayName")
    return out.get("value", [])


def sp_risk(sp_id):
    """riskyServicePrincipals (P2). A 404 means not risky; other failures are 'unavailable'."""
    try:
        r = graph("GET", f"/identityProtection/riskyServicePrincipals/{sp_id}?$select=riskLevel,riskState")
        return {"riskLevel": r.get("riskLevel", "none"), "riskState": r.get("riskState", "none")}
    except Exception as e:
        if "404" in str(e):
            return {"riskLevel": "none", "riskState": "none"}
        return {"riskLevel": "unknown", "riskState": "unavailable"}


def sp_signin_activity(app_id):
    """Service principal sign-in activity is a BETA endpoint. Returns None if unavailable."""
    try:
        out = graph(
            "GET",
            f"/servicePrincipalSignInActivities?$filter=appId eq '{app_id}'",
            api="beta",
        )
        vals = out.get("value", [])
        return vals[0] if vals else None
    except Exception:
        return None


def collect_evidence(display_name):
    """Gather all posture evidence for one agent identity."""
    app = find_app(display_name)
    if app is None:
        raise ValueError(f"application not found: {display_name}")
    sp = find_sp(app["appId"])
    sp_id = sp["id"] if sp else None
    return {
        "display_name": display_name,
        "app_object_id": app["id"],
        "app_id": app["appId"],
        "sp_id": sp_id,
        "password_credentials": app.get("passwordCredentials", []),
        "key_credentials": app.get("keyCredentials", []),
        "granted_roles": resolve_roles(granted_app_roles(sp_id)) if sp_id else [],
        "federated": federated_credentials(app["id"]),
        "owners": owners(app["id"]),
        "risk": sp_risk(sp_id) if sp_id else {"riskLevel": "unknown", "riskState": "unavailable"},
        "signin": sp_signin_activity(app["appId"]),
    }
