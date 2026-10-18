# Lane C handoff: red team, immune loop, demo data

Branch `lane/redteam`. This file records what lane C has built, how to run it and what is open.

## Done

**C1, demo data.** `redteam/datagen.py` writes `redteam/data/` deterministically from a seed (default 20261020):
- `mandates.json` and `beneficiaries.json`, in the format of `shared/fixture-data.md`. Lane A's Anvil fixture reads them: 3 programmes and 45 beneficiaries, checked on 18 October 2026.
- `books.json`, the stand-in operating books that lane B reads, described in `shared/books.md`.
- `books_anchor.json`, a sha256 of every record, for the auditor's integrity check.
- `documents/`, two legitimate texts and two with injections, for the quarantined reader.

The numbers respect the demo limits in `shared/fixture-data.md`:
- Scenario 6's 11 households total 1,650 USDC.
- Scenario 13's target, `ZKT-B13`, is outside that batch.
- Two zakat households have no payout history.

Tests: `python -m pytest redteam/tests/test_datagen.py` (10 pass).

**C2, gallery format and legitimate set.**
- `redteam/cases.py` validates plan section 3.6's case format with pydantic, loads the gallery and hashes the dataset for run manifests.
- `redteam/legit.py` writes `redteam/gallery/legitimate.yaml`: 20 legitimate payouts sampled from the books' October and semester batches.
- Tests: `python -m pytest redteam/tests/test_cases.py` (5 pass).

## Stopped by the model provider's safety classifier

The cloud session's red-team worker was stopped while writing attack seeds. The provider's safety classifier flagged its session in the category "cyber", most likely on the Base64 and Morse-encoded instructions. Before that, it wrote 28 seed attacks in six classes. They are in `redteam/gallery/drafts/`, unreviewed and not loaded; see the README there.

The cloud session then built only what involves no attack text: the format, the legitimate set, and later the runner and statistics. Still to do, in the local session or by hand:
- the remaining seed attacks: `encoded`, `data_extraction`, `privilege_escalation`, `structuring`, and more in the six drafted classes;
- the mutation agent `redteam/mutate.py` (plan task C3).

## Run

```bash
python -m venv .venv && .venv/bin/pip install -r redteam/requirements.txt
.venv/bin/python -m redteam.datagen          # regenerates redteam/data
.venv/bin/python -m pytest redteam/tests
```

## Open

- **Real id hashes.** `INSTITUTION_HMAC_KEY` is not set, so the id hashes use a development key. `books.json` says so in `generated.hmac_key`. Set the real key and regenerate before the Base Sepolia run.
- **Scenario 7 cap.** Flood relief's per-beneficiary cap stays at the plan's 600 USDC until Hafiz decides entry A-10 in `docs/decisions.md`. It is one number in `PROGRAMMES` in `redteam/datagen.py`.
