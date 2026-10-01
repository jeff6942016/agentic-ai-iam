"""Scope probe: prove the auditor cannot change what it inspects.

The auditor reads the configuration of every agent identity in the tenant, which
makes it a high-value identity. This probe has it attempt a write (adding a
password credential to an application) and confirms the write is refused at the
permission layer, because the auditor holds only read scopes. It is the mirror
of the scope probes in projects 01 and 02.
"""
from iam_tools import nhi_reader as R
from iam_tools.graph_client import graph

TARGET = "jml-agent"  # any agent identity; we only attempt the write, never complete it


def main():
    app = R.find_app(TARGET)
    if app is None:
        print(f"target application not found: {TARGET}")
        return
    try:
        graph(
            "POST",
            f"/applications/{app['id']}/addPassword",
            json={"passwordCredential": {"displayName": "scope-probe"}},
        )
        print("UNEXPECTED: auditor added a credential (over-privileged)")
    except Exception as e:
        print("Blocked at permission layer (expected):", e)


if __name__ == "__main__":
    main()
