"""Deterministic severity floor for NHI posture findings.

As in project 02, the security-relevant judgement lives in code. The model may
raise a finding's severity but can never lower it, so an over-privilege drift or
a risky service principal cannot be explained away as acceptable.
"""
from datetime import datetime, timezone

import yaml

RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def load_manifest(path="manifest/agents.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)["agents"]


def _days_until(iso):
    if not iso:
        return None
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (dt - datetime.now(timezone.utc)).days


def evaluate(spec, evidence):
    """Return a list of (severity, finding) tuples from deterministic rules."""
    findings = []

    # Over-privilege drift: a granted application permission not in the manifest.
    allowed = set(spec.get("allowed_graph_app_roles", []))
    for role in evidence["granted_roles"]:
        if role not in allowed:
            findings.append(("critical", f"over-privilege drift: holds {role}, not in manifest"))

    # Standing secret where the manifest requires federation.
    if spec.get("credential") == "federated" and evidence["password_credentials"]:
        findings.append(("high", "standing client secret present, manifest requires federation"))

    # Credential age and expiry.
    max_age = spec.get("max_credential_age_days")
    for cred in evidence["password_credentials"] + evidence["key_credentials"]:
        days = _days_until(cred.get("endDateTime"))
        if days is None:
            continue
        if days < 0:
            findings.append(("high", "expired credential still present on the identity"))
        elif days <= 14:
            findings.append(("medium", f"credential expires in {days} days"))
        elif max_age is not None and days > max_age:
            findings.append(("low", f"credential lifetime exceeds manifest max of {max_age} days"))

    # Accountability.
    if not evidence["owners"]:
        findings.append(("high", "no owner / sponsor on the identity"))

    # Standing directory roles (if the collector populated them).
    if evidence.get("standing_directory_roles") and not spec.get("allow_standing_directory_roles", False):
        findings.append(("critical", "holds standing directory role(s), manifest forbids standing privilege"))

    # Service principal risk.
    state = evidence["risk"]["riskState"]
    if state in ("atRisk", "confirmedCompromised"):
        findings.append(("critical", "service principal flagged risky by Identity Protection"))
    elif state == "unavailable":
        findings.append(("low", "risk state unavailable, treated as unknown rather than safe"))

    if not findings:
        findings.append(("info", "posture matches manifest"))
    return findings


def floor_severity(findings):
    return max((RANK[s] for s, _ in findings), default=0)


def severity_name(rank):
    for name, value in RANK.items():
        if value == rank:
            return name
    return "info"
