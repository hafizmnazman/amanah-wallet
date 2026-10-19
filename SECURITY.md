# Security

Amanah is a research prototype on test networks. It holds no real money, and nothing in it should be pointed at a mainnet without an independent audit.

## Reporting a vulnerability

Please report privately, through **Report a vulnerability** on this repository's Security tab, not in a public issue. Say which component (the vault, the backend, the checkers, the frontend), how to reproduce it, and what it lets an attacker do. We reply within seven days. There is no bounty.

The findings we care about most are the ones that break a property the project claims:

- a payout that moves without the planner, an auditor of a different model family and the sentinel all signing;
- a payout above a programme's cap, or past 80% of its daily budget, that moves without a trustee;
- money reaching a wallet two trustees did not approve, or a beneficiary past its 30-day cap;
- attacker text reaching the auditor or the sentinel in raw form;
- a way to lower the security posture, or unpause the vault, without two trustees.

## What is already known

The threat model, the trust assumptions and the known risks are in `docs/security-self-assessment.md`. In short: lineage is a label the trustees declare when they register a key, until attestation lands; two colluding trustees defeat the bound; and the auditor sometimes escalates sound first payouts, which delays them without paying anything wrongly. The red team's method and every result, including the nulls, are in `redteam/`; Slither's findings and their triage are in `docs/static-analysis.md`.
