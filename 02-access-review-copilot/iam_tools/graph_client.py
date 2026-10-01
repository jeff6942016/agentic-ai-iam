"""Two-identity Microsoft Graph client.

The security property is in the default: every call is made as the read-only
'reader' identity unless the caller explicitly passes identity='writer'. That
makes accidental writes structurally hard: the writer identity has to be named.
"""
import os
import msal
import requests
from dotenv import load_dotenv

load_dotenv()

AUTHORITY = f"https://login.microsoftonline.com/{os.environ['TENANT_ID']}"
SCOPE = ["https://graph.microsoft.com/.default"]

# identity -> (client-id env var, client-secret env var)
_CREDS = {
    "reader": ("READER_CLIENT_ID", "READER_CLIENT_SECRET"),
    "writer": ("WRITER_CLIENT_ID", "WRITER_CLIENT_SECRET"),
}


def _token(identity):
    if identity not in _CREDS:
        raise ValueError(f"unknown identity: {identity}")
    cid_env, sec_env = _CREDS[identity]
    app = msal.ConfidentialClientApplication(
        os.environ[cid_env],
        authority=AUTHORITY,
        client_credential=os.environ[sec_env],
    )
    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "auth failed"))
    return result["access_token"]


def graph(method, path, identity="reader", **kwargs):
    """Call Microsoft Graph v1.0. Reads run as 'reader' by default.

    Writing a review decision requires identity='writer' explicitly.
    """
    resp = requests.request(
        method,
        f"https://graph.microsoft.com/v1.0{path}",
        headers={"Authorization": f"Bearer {_token(identity)}"},
        **kwargs,
    )
    if not resp.ok:
        # A 404 on riskyUsers is expected (user has no risk record); stay quiet.
        # Surface anything else, since a blind raise hides the real cause.
        is_expected_risk_404 = resp.status_code == 404 and "riskyUsers" in path
        if not is_expected_risk_404:
            print(f"Graph {resp.status_code} ({identity}): {resp.text}")
    resp.raise_for_status()
    return resp.json() if resp.text else {}


if __name__ == "__main__":
    definition_id = os.environ["REVIEW_DEFINITION_ID"]
    instances = graph(
        "GET",
        f"/identityGovernance/accessReviews/definitions/{definition_id}"
        f"/instances?$select=id,status,startDateTime,endDateTime",
    )
    for inst in instances.get("value", []):
        print(inst["id"], inst.get("status"))
