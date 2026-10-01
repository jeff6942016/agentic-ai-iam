"""Agentic NHI posture auditor.

For each agent identity declared in the manifest, the model gathers posture
evidence with the read-only tools and writes a plain-language assessment, then
code applies the deterministic findings and severity floor so the model can
explain but never downgrade a critical finding. Output is logs/posture_report.json.

This auditor is itself a non-human identity and appears in its own manifest, so
it grades its own posture alongside the agents it inspects.
"""
import json
import os

from anthropic import Anthropic

from iam_tools import nhi_reader as R
from iam_tools.audit import log
from iam_tools.severity import evaluate, floor_severity, load_manifest, severity_name

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Confirm the current model string in the Anthropic API docs when you build.
MODEL = "claude-sonnet-5"

TOOLS = [
    {
        "name": "get_evidence",
        "description": "Gather posture evidence (credentials, granted roles, owners, risk) for an agent identity by display name.",
        "input_schema": {
            "type": "object",
            "properties": {"display_name": {"type": "string"}},
            "required": ["display_name"],
        },
    },
]

SYSTEM = """You are a non-human-identity posture auditor. For the agent identity
under review, call get_evidence, then output ONLY a JSON object:
{"assessment": "<two or three sentences on the identity's security posture, citing the evidence>"}

Judge posture on least privilege, credential hygiene (standing secrets, expiry),
accountability (an owner), and Identity Protection risk. Do not minimize a
missing owner, a standing secret, or an over-broad permission. Output no text
other than the JSON."""


def _summarize(evidence):
    """A compact, model-safe view of the evidence (no raw secret material)."""
    return {
        "display_name": evidence["display_name"],
        "has_standing_secret": bool(evidence["password_credentials"]),
        "is_federated": bool(evidence["federated"]),
        "granted_roles": evidence["granted_roles"],
        "owner_count": len(evidence["owners"]),
        "risk_state": evidence["risk"]["riskState"],
    }


def model_assessment(display_name, evidence):
    messages = [{"role": "user", "content": f"Review the posture of agent identity '{display_name}'."}]
    while True:
        resp = client.messages.create(
            model=MODEL, max_tokens=600, system=SYSTEM, tools=TOOLS, messages=messages
        )
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(_summarize(evidence)),
                    })
            messages.append({"role": "user", "content": results})
        else:
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            try:
                return json.loads(text).get("assessment", text)
            except Exception:
                return text


def audit_all():
    manifest = load_manifest()
    report = []
    for name, spec in manifest.items():
        try:
            evidence = R.collect_evidence(name)
        except ValueError as e:
            print(f"{name}: SKIPPED ({e})")
            continue

        findings = evaluate(spec, evidence)
        floor = floor_severity(findings)
        sev = severity_name(floor)
        assessment = model_assessment(name, evidence)

        entry = {
            "identity": name,
            "severity": sev,
            "findings": [f for _, f in findings],
            "assessment": assessment,
            "has_standing_secret": bool(evidence["password_credentials"]),
            "is_federated": bool(evidence["federated"]),
            "owner_count": len(evidence["owners"]),
            "granted_roles": evidence["granted_roles"],
            "risk": evidence["risk"]["riskState"],
        }
        report.append(entry)
        log("nhi-auditor", "posture", identity=name, severity=sev, findings=len(findings))
        print(f"{name}: {sev.upper()}  ({len(findings)} finding(s))")
        for _, f in findings:
            print(f"    - {f}")

    os.makedirs("logs", exist_ok=True)
    with open("logs/posture_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nWrote posture for {len(report)} identities to logs/posture_report.json")
    return report


if __name__ == "__main__":
    audit_all()
