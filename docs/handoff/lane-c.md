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

## Run

```bash
python -m venv .venv && .venv/bin/pip install -r redteam/requirements.txt
.venv/bin/python -m redteam.datagen          # regenerates redteam/data
.venv/bin/python -m pytest redteam/tests
```

## Open

- **Real id hashes.** `INSTITUTION_HMAC_KEY` is not set, so the id hashes use a development key. `books.json` says so in `generated.hmac_key`. Set the real key and regenerate before the Base Sepolia run.
- **Scenario 7 cap.** Flood relief's per-beneficiary cap stays at the plan's 600 USDC until Hafiz decides entry A-10 in `docs/decisions.md`. It is one number in `PROGRAMMES` in `redteam/datagen.py`.
