"""Human-in-the-loop approval gate.

Reads the agent's recommendations, shows each with its evidence, and lets a
person decide what to submit. Only after a person confirms does the writer
identity record a decision. 'confirm' verdicts are escalated to a manager and
never auto-submitted.

Dry run by default:
    python review_approve.py            # shows what would be submitted
    python review_approve.py --live     # actually records decisions
"""
import json
import os
import sys

from iam_tools import review_reader as reader
from iam_tools.audit import log
from iam_tools.review_writer import record_decision

# keep -> Approve (access stays), revoke -> Deny (Entra auto-apply removes it)
VERDICT_TO_DECISION = {"keep": "Approve", "revoke": "Deny"}


def main(live=False):
    definition_id = os.environ["REVIEW_DEFINITION_ID"]
    instance = reader.active_instance(definition_id)
    with open("logs/recommendations.json") as f:
        recommendations = json.load(f)

    for rec in recommendations:
        verdict = rec["final_verdict"]
        label = "ESCALATE to manager" if verdict == "confirm" else VERDICT_TO_DECISION[verdict]
        print(f"\n{rec['user']}  ->  {verdict}  ({label})")
        print(f"   why: {rec['justification']}")
        print(f"   evidence: {rec['evidence']}")

        if verdict == "confirm":
            log("human", "escalate", user=rec["user"])
            continue

        answer = input("   submit this decision? (y/n): ").strip().lower()
        if answer != "y":
            print("   skipped")
            continue

        decision = VERDICT_TO_DECISION[verdict]
        record_decision(
            definition_id,
            instance["id"],
            rec["decision_id"],
            decision,
            rec["justification"],
            dry_run=not live,
        )
        log("review-writer", "record_decision", user=rec["user"], decision=decision, live=live)


if __name__ == "__main__":
    main(live="--live" in sys.argv)
