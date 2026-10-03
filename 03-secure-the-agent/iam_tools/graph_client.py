"""Read-only Microsoft Graph client for the NHI posture auditor.

This project has exactly one identity and it is read-only. There is no writer,
by design: a tool that reads the configuration of every non-human identity in
the tenant must not also be able to change what it inspects. The auditor can be
run interactively with a client secret during development, or via workload
identity federation in CI (see federation/), in which case no secret is stored.
"""
import os

import msal
import requests
from dotenv import load_dotenv

load_dotenv()

AUTHORITY = f"https://login.microsoftonline.com/{os.environ['TENANT_ID']}"
SCOPE = ["https://graph.microsoft.com/.default"]


def _token():
    """Acquire a token for the auditor app.

    Prefers a client-assertion (federated / certificate) when CLIENT_ASSERTION is
    present in the environment, otherwise falls back to a client secret for local
    development. The federated path is what removes the standing secret in CI.
    """
    client_id = os.environ["AUDITOR_CLIENT_ID"]
    assertion = os.environ.get("AUDITOR_CLIENT_ASSERTION")
    if assertion:
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=AUTHORITY,
            client_credential={"client_assertion": assertion},
        )
    else:
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=AUTHORITY,
            client_credential=os.environ["AUDITOR_CLIENT_SECRET"],
        )
    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "auth failed"))
    return result["access_token"]


def graph(method, path, api="v1.0", **kwargs):
    """Call Microsoft Graph. `api` is 'v1.0' or 'beta' (sign-in activity is beta)."""
    resp = requests.request(
        method,
        f"https://graph.microsoft.com/{api}{path}",
        headers={"Authorization": f"Bearer {_token()}"},
        **kwargs,
    )
    if not resp.ok:
        # Some failures are expected and handled by callers; don't print them.
        #  - 404 on riskyServicePrincipals: the SP has no risk record
        #  - any error on the beta servicePrincipalSignInActivities endpoint:
        #    unavailable in many tenants, callers already degrade to None
        is_expected_risk_404 = resp.status_code == 404 and "riskyServicePrincipals" in path
        is_signin_beta = "servicePrincipalSignInActivities" in path
        if not (is_expected_risk_404 or is_signin_beta):
            print(f"Graph {resp.status_code} ({api}): {resp.text}")
    resp.raise_for_status()
    return resp.json() if resp.text else {}


if __name__ == "__main__":
    # Smoke test: confirm the auditor can read applications.
    apps = graph("GET", "/applications?$top=5&$select=displayName,appId")
    for a in apps.get("value", []):
        print(a.get("displayName"), "-", a.get("appId"))
