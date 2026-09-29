import json
import uuid
from datetime import datetime, timezone
from iam_tools.audit import log_action

PENDING_FILE = "logs/approvals_pending.json"

def _load_pending():
    if not os.path.exists(PENDING_FILE):
        return []
    with open(PENDING_FILE) as f:
        return json.load(f)

def _add_pending(user_id, group, role):
    os.makedirs("logs", exist_ok=True)
    items = _load_pending()
    items.append({
        "id": str(uuid.uuid4())[:8],
        "user_id": user_id,
        "group": group,
        "role": role,
        "requested_by": "jml-agent",
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    })
    with open(PENDING_FILE, "w") as f:
        json.dump(items, f, indent=2)

TOOLS = [
    {
        "name": "create_user",
        "description": "Create a new user account in Entra ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "display_name": {"type": "string"},
                "upn": {"type": "string", "description": "user principal name, the email-style login"},
                "temp_password": {"type": "string"},
            },
            "required": ["display_name", "upn", "temp_password"],
        },
    },
    {
        "name": "assign_role_access",
        "description": "Assign all group entitlements for a named role from policy. Use this instead of adding groups one by one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "role": {"type": "string", "description": "a role name defined in policy, e.g. financial_analyst"},
            },
            "required": ["user_id", "role"],
        },
    },
    {
        "name": "disable_user",
        "description": "Disable a user account (the leaver action).",
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "string"}},
            "required": ["user_id"],
        },
    },
]

import yaml
from iam_tools.actions import create_user, add_to_group, disable_user, get_group_id

def load_policy():
    with open("policy/roles.yaml") as f:
        return yaml.safe_load(f)

def assign_role_access(user_id, role, dry_run=True):
    policy = load_policy()
    if role not in policy["roles"]:
        log_action("assign_role_access", role, "refused_unknown_role",
                   user_id=user_id)
        return {"error": f"unknown role {role}, refused"}
    groups = policy["roles"][role]["groups"]
    privileged = set(policy.get("privileged_groups", []))
    results = []
    for name in groups:
        if name in privileged:
            _add_pending(user_id, name, role)
            log_action("hold_privileged", name, "held_for_approval",
                       user_id=user_id, role=role)
            results.append({"group": name, "status": "HELD_FOR_APPROVAL"})
        else:
            add_to_group(user_id, get_group_id(name), dry_run=dry_run)
            log_action("add_to_group", name,
                       "dry_run" if dry_run else "assigned",
                       user_id=user_id, role=role, mode="auto")
            results.append({"group": name, "status": "assigned"})
    return results

def run_tool(name, args, dry_run=True):
    if name == "create_user":
        result = create_user(**args, dry_run=dry_run)
        log_action("create_user", args.get("upn", "?"),
                   "dry_run" if dry_run else "created", mode="auto")
        return result
    if name == "assign_role_access":
        return assign_role_access(**args, dry_run=dry_run)
    if name == "disable_user":
        result = disable_user(**args, dry_run=dry_run)
        log_action("disable_user", args.get("user_id", "?"),
                   "dry_run" if dry_run else "disabled", mode="auto")
        return result
    log_action("unknown_tool", name, "refused")
    return {"error": f"unknown tool {name}"}

import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM = """You are an IAM provisioning assistant for Entra ID.
Map each request to actions using ONLY the tools provided.
Never invent group names. To grant access, call assign_role_access with a role name.
For a joiner, create the user first, then assign role access using the returned user id.
For a leaver, disable the user. Explain your plan before acting."""

def handle_ticket(ticket_text, dry_run=True):
    messages = [{"role": "user", "content": ticket_text}]
    while True:
        response = client.messages.create(
            model="claude-sonnet-5",   # confirm current model string in the API docs
            max_tokens=1024,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"Agent wants to run: {block.name} with {block.input}")
                    result = run_tool(block.name, block.input, dry_run=dry_run)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            print(response.content[0].text)
            return

if __name__ == "__main__":
    handle_ticket(
    "Do the onboarding for Daniel Radcliffe as a financial_analyst, daniel.radcliffe@jeffreylpfyahoo.onmicrosoft.com",
    dry_run=False
    )