# Runbook: from keys to the email

The steps left after the cloud session, in order, with the command for each and how to tell it worked. `HANDOFF.md` explains why each step is needed; this file is what to type. Every command runs from the repository root unless it says otherwise, with `.venv` set up as `HANDOFF.md` describes.

The deadline is Tuesday 20 October 2026, 23:59 Malaysia time, and the plan wants the email sent before Tuesday 20:00.

## 1. Pull and check (30 minutes)

```bash
git checkout lane/release && git pull
bash scripts/test_all.sh            # every suite; about 3 minutes
```

Done when every line prints `pass`, except the Anvil demo, which shows 16 of 17 until step 2.

## 2. Decisions and data (Hafiz, 30 minutes)

```bash
git apply docs/patches/a10-flood-cap-1500.patch && git commit -am "Raise the flood relief per-beneficiary cap to 1,500 USDC (decision A-10)"
git apply --index docs/patches/licence-mit.patch && git commit -m "License the project under MIT"
# Put INSTITUTION_HMAC_KEY in .env, then regenerate the data with it:
(set -a && . ./.env && set +a && .venv/bin/python -m redteam.datagen)
cp redteam/data/mandates.json redteam/data/beneficiaries.json contracts/test/fixtures/
bash scripts/test_all.sh
git add redteam/data contracts/test/fixtures && git commit -m "Regenerate the demo data with the institution's HMAC key"
```

Done when `test_all.sh` passes everywhere and the Anvil demo shows 17 of 17. If you choose A-10's second option instead, change `REQ-REL-0001` in `redteam/datagen.py` as `docs/patches/README.md` says.

## 3. Deploy on Base Sepolia (A6, 30 minutes)

```bash
.venv/bin/python scripts/preflight.py --stage deploy      # fix every FAIL first
cd contracts
(set -a && . ../.env && set +a && forge script script/Deploy.s.sol --rpc-url base_sepolia --broadcast --verify)
cd ..
git add contracts/deployments/84532.json contracts/broadcast/Deploy.s.sol/84532 && git commit -m "Deploy and verify AmanahVault on Base Sepolia"
```

Done when the source shows as verified on sepolia.basescan.org and `contracts/deployments/84532.json` is committed. Put `VAULT_ADDRESS` in `.env`.

## 4. Live models (30 minutes)

```bash
.venv/bin/python scripts/preflight.py --stage models
(cd backend && set -a && . ../.env && set +a && ../.venv/bin/python -m pytest -m live)   # four small paid calls
.venv/bin/python scripts/run_demo.py --network anvil --live
```

Done when the four live tests pass and the live Anvil demo shows 17 of 17. If the live planner reads the scripted conversation differently, `docs/demo-transcript.md` and `backend/app/agentwallet/prompts/planner.md` are where to look.

## 5. Red team (Monday night, a few hours)

1. Review the draft seeds in `redteam/gallery/drafts/`, write the rest to reach 40 with 4 per class, and move the reviewed files up one folder.
2. Build `redteam/mutate.py` (plan task C3), then `python -m redteam.mutate --n 3`.
3. Fill the model names and case counts in `redteam/protocol.md`, and commit it on its own. That commit must come before the full run.
4. Run it:

```bash
.venv/bin/python scripts/preflight.py --stage redteam
# PLANNER_REFUSAL_FALLBACK=off in .env for this run
(set -a && . ./.env && set +a && .venv/bin/python -m redteam.run --config redteam/configs/full.yaml --anvil --run-id final)
git add redteam/results/final && git commit -m "Add the red team's full run"
```

Done when `redteam/results/final/report.md` exists and is committed after the protocol. `--run-id final` makes the runner write into `redteam/results/final/`.

## 6. Base Sepolia demo (1 hour)

```bash
.venv/bin/python scripts/preflight.py --stage demo        # gas, the donor's 5,000 USDC, trustee roles, the HMAC key
.venv/bin/python scripts/run_demo.py --network base-sepolia --live
.venv/bin/python scripts/verify.py --csv evidence/transactions.csv
.venv/bin/python scripts/evidence_pack.py
git add evidence && git commit -m "Add the Base Sepolia evidence"
```

Done when the demo prints 17 of 17 and `verify.py` passes on every executed payout. Run it once per vault: a second run meets the 30-day caps and the sentinel's frequency rule (decision B-17).

Start it well clear of 08:00 Malaysia time, which is 00:00 UTC, when the vault's day turns. Scenario 13 needs scenario 6's spend from the same vault day (decision A-11), and the run takes about an hour, 10 minutes of it the cooling-off.

## 7. Frontend and video (2 to 3 hours)

- Set `VITE_VAULT_ADDRESS` and `VITE_CHAIN_ID=84532` in `frontend/.env.local`, and use a MetaMask account registered as a trustee (plan task D3).
- Record the shots in `docs/video-shot-list.md`. The opening is `python scripts/split_screen.py --live` with a message the live S1 arm fell for.

## 8. Documents (2 hours)

```bash
git apply docs/patches/readme-e4-fills.patch && git commit -am "Apply the README audit's fixes"
.venv/bin/python scripts/fill_readme.py --readme docs/submission-readme.md          # read the changes
.venv/bin/python scripts/fill_readme.py --readme docs/submission-readme.md --write
.venv/bin/python scripts/build_deck.py --pdf --team "..." --members "..."
```

Then by hand:
- the markers `fill_readme.py` lists as left: the team, the video and deck links, the pilot outreach and the two sentences on what the results show;
- the status lines at the top of `docs/technical-documentation.md` and `docs/security-self-assessment.md`;
- move `docs/submission-readme.md` into `README.md`;
- read every deck slide against the README.

## 9. Package and send (1 hour)

```bash
.venv/bin/python scripts/presubmit.py --links --verify
```

Done when it prints no FAIL. Then work through its `todo` lines: make the repository public, open every link from a logged-out browser, merge the lanes into `main` in the order A to E, put the video and deck on OneDrive, and send the email from `docs/submission-email.md` before Tuesday 20:00.
