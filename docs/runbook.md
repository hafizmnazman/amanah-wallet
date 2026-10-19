# Runbook: from keys to the email

The steps left, in order, with the command for each and how to tell it worked. `HANDOFF.md` explains why each step is needed; this file is what to type. Every command runs from the repository root of the WSL run copy (`wsl -d Ubuntu`, then `cd ~/amanah-wallet`), with `.venv` set up as `docs/PATHS.md` describes (decision E-17).

The deadline is Tuesday 20 October 2026, 23:59 Malaysia time, and the plan wants the email sent before Tuesday 20:00.

## 1. Pull and check (done 19 October, 03:30)

```bash
git checkout lane/release && git pull
bash scripts/test_all.sh            # every suite; about 3 minutes
```

Done when every line prints `pass`. On 19 October every suite passed in WSL once the trustee page's summary could wrap on a 390 px phone (`5a2e62a`).

## 2. Decisions and data (done 19 October, 03:50)

Hafiz chose on 19 October: decision A-10's option 1, a test token (A-12), new test wallets (E-16), MIT, and re-authoring the cloud commits before going public (E-18).

```bash
git apply docs/patches/a10-flood-cap-1500.patch && git commit -am "..."      # 5c2b078
git apply --index docs/patches/licence-mit.patch && git commit -m "..."      # 61c9e0e
.venv/bin/python scripts/new_keys.py                                          # every key and INSTITUTION_HMAC_KEY in .env
INSTITUTION_HMAC_KEY=$(grep "^INSTITUTION_HMAC_KEY=" .env | cut -d= -f2) .venv/bin/python -m redteam.datagen
cp redteam/data/mandates.json redteam/data/beneficiaries.json contracts/test/fixtures/   # 233cec2
```

The Anvil demo then gave 17 of 17.

## 3. Fund the wallets (done 19 October, 15:40)

1. Send at least 0.006 Base Sepolia ETH to the relayer from a faucet; 0.01 is comfortable (decision E-20). `python scripts/new_keys.py` prints its address again; it changes nothing on a second run.

   On 19 October no Base Sepolia faucet would pay a fresh address: Coinbase's asked for a phone number, and Alchemy's and QuickNode's for ETH on mainnet. The way round is Ethereum Sepolia ETH, from Google Cloud's faucet or pk910's proof-of-work faucet, sent to the relayer and bridged with Base's L1StandardBridge on Sepolia. On 19 October its `OTHER_BRIDGE` answered the L2 bridge `0x4200000000000000000000000000000000000010`. The ETH reaches the same address on Base Sepolia within minutes; keep a little on Sepolia for the deposit's gas:

   ```bash
   . ~/.amanah_env; key=$(grep "^RELAYER_KEY=" .env | cut -d= -f2)
   cast send 0xfd0Bf71F60660E2f608ed56e1659C450eB113120 "depositETH(uint32,bytes)" 200000 0x \
     --value 0.04ether --private-key "$key" --rpc-url https://ethereum-sepolia-rpc.publicnode.com
   ```
2. Put `RPC_URL`, a Base Sepolia endpoint, in `.env`. Verification needs no key: `VERIFIER_URL` names Blockscout's (decision A-13).
3. Top up the other sending keys from the relayer:

```bash
.venv/bin/python scripts/fund_keys.py           # prints the transfers and sends nothing
.venv/bin/python scripts/fund_keys.py --send
```

Done when `fund_keys.py` prints `every sending key already holds enough`.

## 4. Deploy the token and the vault on Base Sepolia (A6, done 19 October, 15:47)

```bash
cd contracts
(set -a && . ../.env && set +a && forge script script/DeployToken.s.sol --rpc-url base_sepolia --broadcast \
  --verify --verifier blockscout --verifier-url "$VERIFIER_URL")
cd ..
# set USDC_ADDRESS in .env to the TestUSDC address it printed (also in contracts/deployments/84532-token.json)
.venv/bin/python scripts/preflight.py --stage deploy      # fix every FAIL first
cd contracts
(set -a && . ../.env && set +a && forge script script/Deploy.s.sol --rpc-url base_sepolia --broadcast \
  --verify --verifier blockscout --verifier-url "$VERIFIER_URL")
cd ..
git add contracts/deployments/84532.json contracts/deployments/84532-token.json contracts/broadcast/DeployToken.s.sol/84532 contracts/broadcast/Deploy.s.sol/84532
git commit -m "Deploy and verify TestUSDC and AmanahVault on Base Sepolia"
```

Done when both sources show as verified on base-sepolia.blockscout.com and both deployment records are committed. Put `VAULT_ADDRESS` in `.env`.

## 5. Live models (done 19 October: 4 of 4 live tests, 17 of 17 on Anvil)

```bash
.venv/bin/python scripts/preflight.py --stage models
(cd backend && set -a && . ../.env && set +a && ../.venv/bin/python -m pytest -m live)   # four small paid calls
.venv/bin/python scripts/run_demo.py --network anvil --live
```

Done when the four live tests pass and the live Anvil demo shows 17 of 17. If the live planner reads the scripted conversation differently, `docs/demo-transcript.md` and `backend/app/agentwallet/prompts/planner.md` are where to look.

## 6. Red team (done 19 October, 17:55: no transfer attack past S3, 2 of 20 sound payouts escalated)

Done this way: the 44 seeds reviewed and moved up (`99e552f`), C3 skipped by choice (C-14), the protocol committed alone (`ffa0490`), and the full run twice. The first (`redteam/results/final-1/`) found decision B-25; the repeat is `redteam/results/final/` (`163514d`). Its report carries both deviations (C-15), and the evidence pack holds it (`223e051`). To run it again:

1. Review the 44 draft seeds in `redteam/gallery/drafts/` with `REVIEW.md` there, and move the reviewed files up one folder. 40 seeds with 4 per class are needed.
2. Settle plan task C3 (decision C-14): write `redteam/mutate.py` and run `python -m redteam.mutate --n 3`, or run without a mutated set and say so in the protocol.
3. Fill the model names and case counts in `redteam/protocol.md`, and commit it on its own. That commit must come before the full run.
4. Run it:

```bash
.venv/bin/python scripts/preflight.py --stage redteam
# PLANNER_REFUSAL_FALLBACK=off in .env for this run
(set -a && . ./.env && set +a && .venv/bin/python -m redteam.run --config redteam/configs/full.yaml --anvil --run-id final)
git add redteam/results/final && git commit -m "Add the red team's full run"
```

Done when `redteam/results/final/report.md` exists and is committed after the protocol. `--run-id final` makes the runner write into `redteam/results/final/`. A deviation goes in the run's `DEVIATIONS.md`; `python -m redteam.report redteam/results/final` then renders the report again from `results.jsonl`, with it at the end, and calls no model.

## 7. Base Sepolia demo (done 19 October, 16:28: 17 of 17 with live models)

```bash
.venv/bin/python scripts/preflight.py --stage demo        # gas, the donor's 5,000 USDC, trustee roles, the HMAC key
.venv/bin/python scripts/run_demo.py --network base-sepolia --live
.venv/bin/python scripts/verify.py --csv evidence/transactions.csv
.venv/bin/python scripts/evidence_pack.py
git add evidence && git commit -m "Add the Base Sepolia evidence"
```

Done when the demo prints 17 of 17 and `verify.py` passes on every executed payout. Run it once per vault: a second run meets the 30-day caps and the sentinel's frequency rule (decision B-17). The token's spare 15,000 covers a second vault if one is needed.

Before the first payout the demo waits, with progress printed, while the sentinel reads the vault's payout history (decision B-21). On a provider that serves logs ten blocks at a time, as Alchemy's free plan does, a day of blocks takes minutes; a paid plan, or a provider without that cap, is faster. Deploy shortly before the demo if you can.

Start it well clear of 08:00 Malaysia time, which is 00:00 UTC, when the vault's day turns. Scenario 13 needs scenario 6's spend from the same vault day (decision A-11). The run has not been timed on Base Sepolia; expect under an hour: about 90 transactions, the live model calls, and the 10-minute cooling-off.

## 8. Frontend and video (2 to 3 hours)

- Record the shots in `docs/video-shot-list.md`, which says how to start everything. The browser shots run on the local stack with the live models (`bash scripts/dev_up.sh --live`), because the Base Sepolia vault already paid this month's households; the chain shots are the Base Sepolia run's transactions on Blockscout (decision E-25). The opening is `python scripts/split_screen.py --live --message-file docs/video/split-screen-message.txt`: seed `urgency-001`, which the live S1 arm paid and every checker rejected.
- MetaMask for the trustee shot: a network for the local chain (RPC http://127.0.0.1:8545, chain id 31337) and Anvil's account 5, the fixture's trustee 1.
- **The trustee's real signature on Base Sepolia (plan task D3, decision E-35), with Hafiz at the keyboard.** Household ZKT-H14 (160 USDC) is the payout: the vault has never paid it.
  1. MetaMask in Edge or Chrome, on Base Sepolia (chain id 84532), with the key `grep ^TRUSTEE1_KEY .env` shows imported. It needs no ETH: the relayer sends the transaction.
  2. Terminal 1: `.venv/bin/python scripts/sepolia_up.py` (API 8020, auditor 8121, sentinel 8122; evidence in `evidence/sepolia-trustee/`).
  3. Terminal 2: `cd frontend && VITE_MOCK_API=0 VITE_API_URL=http://127.0.0.1:8020 VITE_CHAIN_ID=84532 VITE_VAULT_ADDRESS=0x558e8E8b2E20D41cE763A2c0FdC1d2c8A5B34FC5 VITE_RPC_URL=https://sepolia.base.org VITE_EXPLORER_URL=https://base-sepolia.blockscout.com VITE_DEV_SIGNING=0 npx vite --port 5174`.
  4. `.venv/bin/python scripts/trustee_session.py raise`: the posture goes to 1, so the next routine payout waits for a trustee.
  5. At http://127.0.0.1:5174, as Finance Officer: "Pay household ZKT-H14 this month.", then Confirm. The payout shows Waiting for a Trustee.
  6. Switch to Trustee, Connect MetaMask, check the decoded fields against the summary, Sign in MetaMask. The row turns Paid with a Blockscout link.
  7. `.venv/bin/python scripts/trustee_session.py lower`, then commit `evidence/sepolia-trustee/` (its `*.log` files are ignored).

## 9. Documents (2 hours)

```bash
git apply docs/patches/readme-e4-fills.patch && git commit -am "Apply the README audit's fixes"   # done, 33ca7e6
.venv/bin/python scripts/fill_readme.py          # done 19 October; it now reads README.md and lists what is left
.venv/bin/python scripts/build_deck.py --pdf --team "Amanah" --members "Abdul Hafiz Bin Mohd Noor Azman, Muhammad Khaidhir Bin Mohd Razin"   # done 19 October
```

Then by hand:
- the markers `fill_readme.py` lists as left: the team and members, the video and deck links, the team's details and the supervision line (the pilot outreach and the reading of the results are done);
- the README's USDC rows: the demo token's address, and why it is not Circle's (decision A-12); done, `3004f0e`;
- the README's hard-coded Basescan links, such as the vault's address row: Blockscout, where the source is verified (decision A-13); done, `3004f0e`;
- the status lines at the top of `docs/technical-documentation.md` and `docs/security-self-assessment.md`; done, `099ef44`;
- move `docs/submission-readme.md` into `README.md`; done, in the house style (decision E-23);
- read every deck slide against the README.

## 10. Package and send (1 hour)

```bash
.venv/bin/python scripts/presubmit.py --links --verify
```

Done when it prints no FAIL. Then work through its `todo` lines, in this order:
1. with Hafiz's go, fast-forward `main` to `lane/release`: `git checkout main && git merge --ff-only lane/release && git push origin main`. This is the merge in the order A to E; checked on 19 October in a throwaway worktree: `main` is an ancestor of `lane/release`, which already holds every lane, merged in the order A and B, C, D. Merging lane by lane from `main` instead stops at lane C on a `docs/decisions.md` conflict that `lane/release` resolved on 18 October;
2. re-author the cloud session's commits and force-push once, with Hafiz's go at that moment (decision E-18), then clone again;
3. make the repository public, and open every link from a logged-out browser;
4. put the video and deck on OneDrive;
5. send the deliverables email (the draft is kept outside the repository, beside the registration email) before Tuesday 20:00.
