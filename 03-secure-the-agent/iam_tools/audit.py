"""Structured attribution logging for the posture auditor."""
import json
import os
from datetime import datetime, timezone

LOG_PATH = os.path.join("logs", "audit.jsonl")


def log(actor, action, **fields):
    os.makedirs("logs", exist_ok=True)
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "actor": actor, "action": action}
    entry.update(fields)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry
