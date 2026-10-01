# Killing the standing secret with workload identity federation

The highest-value NHI hardening in this project: replace an agent's stored client
secret with a federated credential, so the automated runtime holds only a
short-lived token and there is no long-lived secret to steal.

## Why federation, not a client secret

| Aspect | Client secret | Workload identity federation |
| :--- | :--- | :--- |
| What is stored | A long-lived secret value in a vault or `.env` | Nothing; trust is a configured relationship |
| If exfiltrated | Full agent access until the secret expires | No stored secret to exfiltrate for the automated path |
| Rotation | Manual, and often forgotten | No secret to rotate |
| Blast radius | Whole secret lifetime | A single short-lived, audience-bound token |

## Configure it (GitHub Actions as the OIDC issuer)

1. In the agent's app registration: Certificates & secrets, Federated credentials,
   Add a credential, scenario "GitHub Actions deploying Azure resources".
2. Set:
   - Issuer: `https://token.actions.githubusercontent.com`
   - Subject: `repo:jeff6942016/agentic-ai-iam:ref:refs/heads/main`
   - Audience: `api://AzureADTokenExchange`
   - Name: a label such as `github-main`.
3. Save. The app now trusts OIDC tokens minted by that repo and branch.

## Run with no secret

See `github-actions-auth.yml`. The workflow requests an OIDC token
(`permissions: id-token: write`) and exchanges it for a Graph token. No client
secret is stored in the repo or in the environment.

## Realize the benefit

Once the federated run succeeds, delete the client secret on that app
registration. Re-run `python -m auditor.posture_agent`: the "standing client
secret present" finding for that identity clears and `is_federated` flips to
true. That before-and-after is the proof.

## Honest scope

Federation removes the stored secret for the agent's automated (CI or scheduled)
path, which is the production pattern. Interactive local development still uses a
short-lived token acquired another way, so the claim is "no standing secret for
the automated runtime," not "no credentials anywhere."
