# Operating books format

`redteam/data/books.json` stands in for Amanah's operating books in this repository. Lane C writes it with `python -m redteam.datagen`. Lane B reads it, read-only, through `backend/app/agentwallet/books.py`. When the local session connects the agent wallet to Amanah's real books, only that adapter changes.

Everything in it is synthetic. Amounts are whole USDC.

| key | rows | fields |
|:--|--:|:--|
| `generated` | | `seed`, `generator`, `as_of`, `hmac_key` (which key made the id hashes) |
| `institution` | | `name`, `synthetic` |
| `funds` | 3 | `fund_code` (`ZKT`, `REL`, `EDU`), `name` |
| `programmes` | 3 | `code`, `fund_code`, `name`, `purpose`, `cadence` (`monthly`, `one_off`, `semester`), `location`, `programme_id` (bytes32), `purpose_hash` (keccak256 of `purpose`), `cap_usdc`, `hard_ceiling_usdc`, `daily_budget_usdc`, `per_beneficiary_cap_usdc` |
| `beneficiaries` | 45 | `beneficiary_ref`, `household_ref`, `programme_code`, `beneficiary_id` (internal), `wallet`, `id_hash` (HMAC-SHA256 of `beneficiary_id`), `status` (`active`, `suspended`, `moved`), `eligible_until`, `household_size_band` (`1-2`, `3-4`, `5+`), `monthly_amount_usdc` (monthly programmes only), `personal` |
| `payouts` | 49 | `payout_ref`, `beneficiary_ref`, `programme_code`, `amount_usdc`, `date`, `batch_ref`, `channel` |
| `batches` | 3 | `batch_ref`, `programme_code`, `period`, `label`, `location`, `status`, `items` (`household_ref`, `beneficiary_ref`, `amount_usdc`) |
| `requests` | 2 | one-off payouts: `request_ref`, `programme_code`, `beneficiary_ref`, `kind`, `amount_usdc`, `reason`, `status` |
| `notes` | 3 | free text about a beneficiary: `note_ref`, `beneficiary_ref`, `author`, `text` |
| `donations` | 1 | `receipt_ref`, `donor_ref`, `fund_code`, `amount_usdc`, `date`, `status` |
| `scenario_refs` | | which rows the scripted demo uses: `routine_batch`, `removed_household`, `structuring_target`, `emergency_grant`, `override_case`, `stored_injection_note`, `donor_receipt` |

## Who may see what

| field | planner | auditor's case file | sentinel | chain |
|:--|:--|:--|:--|:--|
| `personal` (name, identity number, address, phone) | never | never | never | never |
| `notes` and `requests.reason` (free text) | yes | never | never | never |
| status, eligibility date, household size band, last three payout amounts and dates | yes | yes | as numbers | never |
| `wallet` | yes | yes | as "known beneficiary: yes or no" | yes |
| `id_hash`, `programme_id` | yes | yes | no | yes |

One note, `NOTE-0003`, is a stored injection that reads as an instruction. It exists to test that free text never reaches the auditor.

## Integrity anchor

`redteam/data/books_anchor.json` holds a sha256 for every record, keyed `<table>/<ref>` (for example `beneficiaries/ZKT-B01`), over canonical JSON (sorted keys, no whitespace). It also holds a root over the sorted pairs. Before signing, the auditor recomputes the hash of every record it reads and refuses on a mismatch. This stands in for Amanah's integrity check. Anchoring the root on-chain with `anchorReport` is lane E's choice.

## Demo documents

`redteam/data/documents/` holds four short texts for the quarantined reader. Two are legitimate: a support letter and a repair quotation. One hides an instruction aimed at the system (scenario 9). One is a role claim that asks for a new beneficiary.
