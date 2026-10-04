# LinkedIn post draft: securing agentic identities

A short post drawn from the capstone. First person, in Jeffrey's voice. Paste
into LinkedIn and trim to taste. No hashtags are required; a few are suggested at
the end.

---

Most conversations about AI agents in security ask what the agent can do. I spent
the last few weeks on a different question: what happens when the agent itself is
the privileged identity?

An autonomous agent that can create accounts or grant access in Entra ID is a
superuser with no human behind it, no second factor, and usually a long-lived
secret sitting in a vault. So I built a small portfolio that treats it as exactly
that, a privileged non-human identity, and governs it like one.

Three projects, one posture:

1. A joiner-mover-leaver agent that provisions access from plain-language tickets,
but can only grant what a policy allows, holds privileged actions for human
approval, and has no permission to assign admin roles at all. I red-teamed it with
prompt injection; it held.

2. An access-review copilot that reads the whole entitlement graph as a read-only
identity and recommends certifications, with a deterministic policy floor so the
model can be stricter but never softer. I attacked it by planting instructions in
a user's job title field; the floor held regardless.

3. The one I am most proud of: a project whose entire subject is securing the
agent identities themselves. A manifest declares each agent's least-privilege
baseline, workload identity federation removes the standing secret, every identity
has an accountable owner, and a read-only auditor grades the posture. On its first
run it caught a real over-privilege I had left in the tenant, which I then
remediated. The tool found a genuine problem, not a staged one.

I mapped the whole thing to NIST AI RMF, SOC 2, the OWASP guidance on LLM and
non-human-identity risk, and the 2026 agentic-identity work from OASIS and CSA.

The takeaway I keep coming back to: the interesting part of agentic AI in security
is not the automation, it is the containment. The agent is a new identity class,
and the teams that get this right will govern it with the same discipline they
already apply to humans and workloads.

Repo in the comments. Always happy to compare notes with people working on
non-human identity.

---

Suggested tags: #IAM #NonHumanIdentity #AgenticAI #CloudSecurity #Entra
Repo link to drop in the first comment: https://github.com/jeff6942016/agentic-ai-iam
