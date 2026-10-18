# Fixture data format

`contracts/script/Fixture.s.sol` reads two files that lane C writes in task C1. Until they exist, it reads the samples in `contracts/test/fixtures/`, which follow the same format. Lane A owns this format; change it only with a note in `docs/decisions.md`.

Both files are JSON. Fields not listed here are ignored, so lane C can add its own.

## `redteam/data/mandates.json`

```json
{
  "programmes": [
    {
      "code": "ZKT-IPOH-FAKIR-M",
      "fund": "Zakat Fund",
      "name": "Ipoh fakir monthly aid",
      "programme_id": "0x...32 bytes",
      "cap_usdc": 200,
      "hard_ceiling_usdc": 1500,
      "daily_budget_usdc": 2500,
      "per_beneficiary_cap_usdc": 400,
      "purpose_hash": "0x...32 bytes"
    }
  ]
}
```

| Field | Type | Meaning |
|:--|:--|:--|
| `code` | string | The programme code from plan section 10 |
| `programme_id` | bytes32 hex | The opaque on-chain id. Make it random so the chain does not reveal the kind of aid |
| `cap_usdc`, `hard_ceiling_usdc`, `daily_budget_usdc`, `per_beneficiary_cap_usdc` | whole USDC, integer | The mandate. The fixture multiplies by 10^6. `cap_usdc` must not exceed `hard_ceiling_usdc` |
| `purpose_hash` | bytes32 hex | Hash of the programme's purpose text |

The fixture sets each mandate active, with an expiry 365 days after deployment.

## `redteam/data/beneficiaries.json`

```json
{
  "beneficiaries": [
    {
      "programme_code": "ZKT-IPOH-FAKIR-M",
      "beneficiary_ref": "ZKT-B01",
      "wallet": "0x...20 bytes",
      "id_hash": "0x...32 bytes"
    }
  ]
}
```

| Field | Type | Meaning |
|:--|:--|:--|
| `programme_code` | string | Must match a `code` in `mandates.json` |
| `beneficiary_ref` | string | The books' reference; not sent on-chain |
| `wallet` | address | The beneficiary's wallet, allowlisted for that programme only |
| `id_hash` | bytes32 hex | `HMAC-SHA256(INSTITUTION_HMAC_KEY, beneficiary_id)`, per plan task C1 |

A wallet may appear under more than one programme; each programme allowlists it separately.

## Numbers the scripted demo depends on

Plan section 10's scenarios only play out as written if the data respects these limits. `contracts/test/Scenarios.t.sol` checks them against the contract.

- **Scenario 6.** The 11 zakat payouts are each at most 200 USDC, and together at most 2,000 USDC (80% of the 2,500 daily budget), so all 11 stay routine.
- **Scenario 13.** For the second 199 USDC payout to cross the 80% line, scenario 6's total that UTC day must be over 1,602 and at most 1,801 USDC. The vault's day starts at 08:00 Malaysia time. The structuring beneficiary must not be one of scenario 6's households.
- **Scenario 7.** The flood relief per-beneficiary cap must be at least the grant. Decision A-10 set it to 1,500 USDC, so the 1,200 USDC grant is elevated and a trustee co-signs it.
- **Scenario 15.** The bursary override must be at most 500 USDC, the per-beneficiary cap, and at most the 1,000 USDC hard ceiling.
