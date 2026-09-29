# Red-team findings: JML provisioning agent

Target: jml-agent (service principal), Entra ID test tenant
Method: adversarial tickets fed to handle_ticket(), run in dry-run then live against test users
Threat frames: OWASP LLM/agentic Top 10, NIST AI RMF (Measure, Manage)

## Defense-in-depth layers under test
1. Prompt layer: the SYSTEM instructions (weakest, model can be talked out of it)
2. Code layer: assign_role_access guardrail (privileged hold, unknown-role refusal)
3. Permission layer: the app registration's Graph scopes (agent lacks the permission entirely)

---

### Attack N: <name>
- Ticket:
- Hypothesis:
- What the agent did:
- Which layer stopped it:
- What was logged (audit.jsonl):
- Production gap / what I'd add: