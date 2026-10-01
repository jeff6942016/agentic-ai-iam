# Agentic AI in Identity and Access Management

![Focus](https://img.shields.io/badge/Focus-Agentic%20AI%20%2B%20IAM-5E5E5E)
![Platform](https://img.shields.io/badge/Platform-Microsoft%20Entra%20ID-0078D4?logo=microsoft&logoColor=white)
![Language](https://img.shields.io/badge/Language-Python-3776AB?logo=python&logoColor=white)
![Security Lens](https://img.shields.io/badge/Security-Non--Human%20Identity-C0392B)

A portfolio of projects at the intersection of agentic AI and identity and access management. The thesis across every project is not "AI applied to IAM" but a security posture: an autonomous agent that can act on identities is a new class of privileged non-human identity, and it is scoped, gated, audited, and red-teamed like one. Each project is anchored to a real IAM pain point, mapped to recognized enterprise controls and frameworks, and documented with an honest account of how it would fail in production.

## Portfolio map

| # | Project | What it proves | Core stack | Status |
| :--- | :--- | :--- | :--- | :--- |
| 01 | [Agentic Joiner-Mover-Leaver Agent](01-jml-agent/README.md) | An agent can run the JML lifecycle in Entra ID while being contained as a least-privilege identity: a policy boundary the model cannot cross, an in-code approval gate for privileged access, full attribution logging, and a red-team pass against the agent itself | Python, Microsoft Graph, Claude tool use, Entra ID P2 (PIM, access reviews, Conditional Access) | Complete |
| 02 | [Agentic Access Review Copilot](02-access-review-copilot/README.md) | An agent can certify access without becoming a risk: it reads the entitlement graph as a read-only identity, a deterministic policy floor backs every verdict, a separate write-scoped identity records decisions only after human sign-off, and a data-injection red team is resisted and backstopped | Python, Microsoft Graph, Claude tool use, Entra ID P2 (access reviews, sign-in recommendations, Identity Protection) | Complete |

Further projects will extend the set across the two halves of the theme: agents that perform IAM work, and the governance of agent identities themselves.

## How to read this repository

Each project lives in its own numbered folder with a self-contained README documenting the build phase by phase, the design decisions and their rejected alternatives, the frameworks it maps to, and a "how this fails in production" section. Screenshots for a project live under that project's `docs/screenshots/` folder.
