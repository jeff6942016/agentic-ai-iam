"""Credential-theft reasoning probe.

This does not exfiltrate anything. It inspects an agent identity's credential
posture and narrates the blast radius of a leaked credential, to make the case
for workload identity federation concrete.

Flow:
  1. Report whether the identity still has a standing client secret. If it does,
     a leaked secret value grants an attacker the identity's full Graph access
     with no user and no second factor, for the secret's whole lifetime.
  2. Report whether the identity uses federated credentials. If it does, there is
     no stored secret to steal for the automated path; the runtime holds only a
     short-lived OIDC-exchanged token.
  3. State the residual control: Conditional Access for workload identities would
     additionally bind a stolen token to known IP ranges and refuse it on
     service-principal risk. That control needs Workload Identities Premium and
     is documented as a design recommendation, not executed here.
"""
import sys

from iam_tools import nhi_reader as R


def main(display_name):
    ev = R.collect_evidence(display_name)
    has_secret = bool(ev["password_credentials"])
    has_fed = bool(ev["federated"])

    print(f"identity: {display_name}")
    print(f"  standing client secret present: {has_secret}")
    print(f"  federated credential present  : {has_fed}")
    print()
    if has_secret:
        print("RISK: a leaked secret grants full agent access, no user, no MFA, until it expires.")
        print("      This is the standing-secret blast radius federation is meant to remove.")
    if has_fed and not has_secret:
        print("CONTAINED: no stored secret for the automated path; runtime holds only a")
        print("           short-lived federated token. Nothing long-lived to exfiltrate.")
    if has_fed and has_secret:
        print("PARTIAL: federation is configured but a standing secret still exists.")
        print("         Remove the secret to realize the benefit.")
    print()
    print("Residual control (design, needs Workload Identities Premium):")
    print("  Conditional Access for workload identities would bind a stolen token to known")
    print("  IP ranges and refuse it on service-principal risk.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m redteam.credential_theft <display_name>")
    main(sys.argv[1])
