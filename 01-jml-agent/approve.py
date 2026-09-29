import json
import os
from datetime import datetime, timezone
from iam_tools.actions import add_to_group, get_group_id
from iam_tools.audit import log_action

PENDING_FILE = "logs/approvals_pending.json"
COMPLETED_FILE = "logs/approvals_completed.json"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)

def save_json(path, items):
    os.makedirs("logs", exist_ok=True)
    with open(path, "w") as f:
        json.dump(items, f, indent=2)

def main():
    pending = load_json(PENDING_FILE)
    waiting = [p for p in pending if p["status"] == "pending"]
    if not waiting:
        print("No privileged access requests pending approval.")
        return

    print("Pending privileged access requests:\n")
    for i, item in enumerate(waiting, 1):
        print(f"  [{i}] user {item['user_id']} -> {item['group']}  "
              f"(role: {item['role']}, requested {item['requested_at']})")

    choice = input("\nApprove which number? ('q' to quit): ").strip()
    if choice.lower() == "q":
        return
    item = waiting[int(choice) - 1]

    confirm = input(f"Grant {item['group']} to {item['user_id']} for real? (yes/no): ").strip()
    if confirm.lower() != "yes":
        print("Cancelled. Nothing granted.")
        return

    # the privileged grant: done by a human, for real
    add_to_group(item["user_id"], get_group_id(item["group"]), dry_run=False)
    log_action("add_to_group", item["group"], "assigned",
               actor="human-approver", mode="approved",
               user_id=item["user_id"], role=item["role"])
    item["status"] = "approved"
    item["approved_at"] = datetime.now(timezone.utc).isoformat()
    save_json(PENDING_FILE, pending)

    completed = load_json(COMPLETED_FILE)
    completed.append(item)
    save_json(COMPLETED_FILE, completed)
    print(f"Granted {item['group']} to {item['user_id']}. Logged to {COMPLETED_FILE}.")

if __name__ == "__main__":
    main()