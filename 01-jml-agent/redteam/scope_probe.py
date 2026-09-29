from iam_tools.graph_client import graph

# Attempt to ASSIGN a directory role directly via Graph, bypassing the agent.
# Assigning Global Administrator needs RoleManagement.ReadWrite.Directory,
# which the app registration was never granted. Graph should refuse with 403.
#
# principalId is a random non-existent GUID on purpose: if the permission were
# somehow present, the request still can't elevate a real user (it 400s on a
# bad principal instead). Missing permission is evaluated first, so we get 403.
GLOBAL_ADMIN_ROLE = "62e90394-69f5-4237-9190-012177145e10"  # well-known template id

body = {
    "@odata.type": "#microsoft.graph.unifiedRoleAssignment",
    "roleDefinitionId": GLOBAL_ADMIN_ROLE,
    "principalId": "00000000-0000-0000-0000-000000000001",
    "directoryScopeId": "/",
}

try:
    graph("POST", "/roleManagement/directory/roleAssignments", json=body)
    print("UNEXPECTED: role assignment write succeeded, agent is over-privileged")
except Exception as e:
    print("Blocked at permission layer (expected):", e)