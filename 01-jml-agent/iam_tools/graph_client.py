import os, msal, requests
from dotenv import load_dotenv

load_dotenv()

AUTHORITY = f"https://login.microsoftonline.com/{os.environ['TENANT_ID']}"
SCOPE = ["https://graph.microsoft.com/.default"]

def get_token():
    app = msal.ConfidentialClientApplication(
        os.environ["CLIENT_ID"],
        authority=AUTHORITY,
        client_credential=os.environ["CLIENT_SECRET"],
    )
    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "auth failed"))
    return result["access_token"]

def graph(method, path, **kwargs):
    resp = requests.request(
        method,
        f"https://graph.microsoft.com/v1.0{path}",
        headers={"Authorization": f"Bearer {get_token()}"},
        **kwargs,
    )
    resp.raise_for_status()
    return resp.json() if resp.text else {}

if __name__ == "__main__":
    users = graph("GET", "/users?$top=5&$select=displayName,userPrincipalName")
    for u in users["value"]:
        print(u["displayName"], "-", u["userPrincipalName"])