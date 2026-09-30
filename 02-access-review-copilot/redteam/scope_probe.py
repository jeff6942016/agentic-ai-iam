"""Scope probe: prove the reader identity cannot write review decisions.

This bypasses the agent and the human gate entirely and tries to record a
decision using the read-only 'reader' identity. It should be refused at the
permission layer, demonstrating that the read/write separation holds in the
consented scopes, not just in the application code path.
"""
import os

from iam_tools import review_reader as reader
from iam_tools.graph_client import graph


def main():
    definition_id = os.environ["REVIEW_DEFINITION_ID"]
    instance = reader.active_instance(definition_id)
    decisions = reader.list_decisions(definition_id, instance["id"])
    if not decisions:
        print("No decision items to probe against.")
        return
    target = decisions[0]["id"]

    try:
        graph(
            "PATCH",
            f"/identityGovernance/accessReviews/definitions/{definition_id}"
            f"/instances/{instance['id']}/decisions/{target}",
            identity="reader",  # deliberately the read-only identity
            json={"decision": "Approve", "justification": "scope probe"},
        )
        print("UNEXPECTED: reader identity recorded a decision (over-privileged)")
    except Exception as e:
        print("Blocked at permission layer (expected):", e)


if __name__ == "__main__":
    main()
