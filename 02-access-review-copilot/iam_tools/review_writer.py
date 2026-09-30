"""Gated decision submission.

This is the ONLY write path in the project, and it can do exactly one thing:
record an Approve or Deny decision on the native access review. It runs as the
'writer' identity, which holds only AccessReview.ReadWrite.All. It is invoked
solely from the human-in-the-loop step (review_approve.py) after a person
confirms. Removal of denied access is performed by Entra's auto-apply, so this
code never touches group membership directly.
"""
from iam_tools.graph_client import graph


def record_decision(definition_id, instance_id, decision_id, decision, justification, dry_run=True):
    if decision not in ("Approve", "Deny"):
        raise ValueError(f"decision must be Approve or Deny, got {decision!r}")
    if dry_run:
        print(f"[DRY RUN] would record {decision} on decision {decision_id}")
        return {"dry_run": True, "decision_id": decision_id, "decision": decision}
    return graph(
        "PATCH",
        f"/identityGovernance/accessReviews/definitions/{definition_id}"
        f"/instances/{instance_id}/decisions/{decision_id}",
        identity="writer",
        json={"decision": decision, "justification": justification},
    )
