from iam_tools.graph_client import graph

def get_group_id(display_name):
    resp = graph("GET",
        f"/groups?$filter=displayName eq '{display_name}'&$select=id,displayName")
    vals = resp.get("value", [])
    if not vals:
        raise ValueError(f"group not found: {display_name}")
    return vals[0]["id"]

def create_user(display_name, upn, temp_password, dry_run=True):
    body = {
        "accountEnabled": True,
        "displayName": display_name,
        "mailNickname": upn.split("@")[0],
        "userPrincipalName": upn,
        "passwordProfile": {
            "forceChangePasswordNextSignIn": True,
            "password": temp_password,
        },
    }
    if dry_run:
        print(f"[DRY RUN] would create user {upn}")
        return {"dry_run": True, "upn": upn, "id": "dry-run-user-id"}
    return graph("POST", "/users", json=body)

def add_to_group(user_id, group_id, dry_run=True):
    if dry_run:
        print(f"[DRY RUN] would add {user_id} to group {group_id}")
        return {"dry_run": True}
    ref = {"@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{user_id}"}
    return graph("POST", f"/groups/{group_id}/members/$ref", json=ref)

def disable_user(user_id, dry_run=True):
    if dry_run:
        print(f"[DRY RUN] would disable {user_id}")
        return {"dry_run": True}
    return graph("PATCH", f"/users/{user_id}", json={"accountEnabled": False})

def get_user_access(user_id):
    return graph("GET", f"/users/{user_id}/memberOf?$select=displayName")

if __name__ == "__main__":
    # dry run first
    result = create_user(
        "Jane Doe",
        "jane.doe@jeffreylpfyahoo.onmicrosoft.com",
        "TempPass!2026",
        dry_run=False,
    )
    print(result)