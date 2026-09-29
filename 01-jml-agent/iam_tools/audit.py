import json
import os
from datetime import datetime, timezone

AUDIT_FILE = "logs/audit.jsonl"

def log_action(action, target, result, actor="jml-agent", mode="auto", **extra):
    os.makedirs("logs", exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "target": target,
        "result": result,
        "mode": mode,
        **extra,
    }
    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry