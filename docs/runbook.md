# Runbook: from keys to the email

The steps left, in order, with the command for each and how to tell it worked. `HANDOFF.md` explains why each step is needed; this file is what to type. Every command runs from the repository root of the WSL run copy (`wsl -d Ubuntu`, then `cd ~/amanah-wallet`), with `.venv` set up as `docs/PATHS.md` describes (decision E-17).

The deadline is Tuesday 20 October 2026, 23:59 Malaysia time, and the plan wants the email sent before Tuesday 20:00.

## 1. Pull and check (done 19 October, 03:30)

```bash
git checkout lane/release && git pull
bash scripts/test_all.sh            # every suite; about 3 minutes
```

Done when every line prints `pass`. On 19 October every suite passed in WSL once the trustee page's summary could wrap on a 390 px phone (`b314612`).

## 2. Decisions and data (done 19 October, 03:50)

Hafiz chose on 19 October: decision A-10's option 1, a test token (A-12), new test wallets (E-16), MIT, and re-authoring the cloud commits before going public (E-18).

```bash
git apply docs/patches/a10-flood-cap-1500.patch && git commit -am "..."      # 5715603
git apply --index docs/patches/licence-mit.patch && git commit -m "..."      # d43a74e
.venv/bin/python scripts/new_keys.py                                          # every key and INSTITUTION_HMAC_KEY in .env
INSTITUTION_HMAC_KEY=$(grep "^INSTITUTION_HMAC_KEY=" .env | cut -d= -f2) .venv/bin/python -m redteam.datagen
cp redteam/data/mandates.json redteam/data/beneficiaries.json contracts/test/fixtures/   # f15afab
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

Done this way: the 44 seeds reviewed and moved up (`cf5d651`), C3 skipped by choice (C-14), the protocol committed alone (`8379854`), and the full run twice. The first (`redteam/results/final-1/`) found decision B-25; the repeat is `redteam/results/final/` (`528274f`). Its report carries both deviations (C-15), and the evidence pack holds it (`0bf2d1b`). To run it again:

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

- **The video, recorded by script (decision E-40), 20 October.** The browser chapters run on the local stack with the live models, because the Base Sepolia vault already paid this month's households; the chain shots are the Base Sepolia run's payout, checked by `scripts/verify.py` and shown on Blockscout (decision E-25). The stack is started from a worktree of its own, since `scripts/dev_up.py` clears `evidence/anvil` and `backend/var/anvil` in the checkout it runs from and would wipe the review stack's:

  ```bash
  git worktree add --detach /root/amanah-media lane/release    # then copy contracts/lib/* in and link .env
  cd /root/amanah-media && AGENTWALLET_SCHEDULE=0 PYTHON=/root/amanah-wallet/.venv/bin/python \
    bash scripts/dev_up.sh --live --anvil-port 8555 --api-port 8010 --auditor-port 8111 --sentinel-port 8112 \
    --cors http://127.0.0.1:5175
  cd /root/amanah-wallet/frontend && VITE_MOCK_API=0 VITE_API_URL=http://127.0.0.1:8010 VITE_CHAIN_ID=31337 \
    VITE_VAULT_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512 VITE_RPC_URL=http://127.0.0.1:8555 \
    VITE_EXPLORER_URL=http://anvil.local VITE_DEV_SIGNING=1 \
    VITE_DEV_TRUSTEE_KEY=$(cast wallet private-key --mnemonic "test test test test test test test test test test test junk" --mnemonic-index 5) \
    npx vite build --outDir /tmp/amanah-rec-dist && npx vite preview --outDir /tmp/amanah-rec-dist --port 5175
  .venv/bin/python scripts/split_screen.py --live --message-file docs/video/split-screen-message.txt --json /tmp/split-live.json
  NODE_PATH=frontend/node_modules node docs/video/record.cjs --out /root/amanah-video/take2 --split /tmp/split-live.json
  .venv/bin/python docs/video/cut.py --raw /root/amanah-video/take2 --work /mnt/c/<a folder> \
    --voice "<project folder>/submission/voice" --metamask <Hafiz's capture> --metamask-span 3,40 --out amanah-demo.mp4
  ```

  Scheduled drafting is off on that stack (`AGENTWALLET_SCHEDULE=0`), so the Officer Desk opens on an empty chat. Each recording needs a fresh chain, because chapter 3 pays the batch and chapter 6 raises the posture: restart the stack first. The opening is seed `urgency-001`, which the live S1 arm paid and every checker rejected. `cut.py --plan` prints each chapter's length against its voice-over without cutting.
- MetaMask for the trustee shot: a network for the local chain (RPC http://127.0.0.1:8545, chain id 31337) and Anvil's account 5, the fixture's trustee 1.
- **The trustee's real signature on Base Sepolia (plan task D3, decision E-35), with Hafiz at the keyboard.** Household ZKT-H14 (160 USDC) is the payout: the vault has never paid it.
  1. MetaMask in Edge or Chrome, on Base Sepolia (chain id 84532), with the key `grep ^TRUSTEE1_KEY .env` shows imported. It needs no ETH: the relayer sends the transaction.
  2. Terminal 1: `.venv/bin/python scripts/sepolia_up.py` (API 8020, auditor 8121, sentinel 8122; evidence in `evidence/sepolia-trustee/`).
  3. Terminal 2: `cd frontend && VITE_MOCK_API=0 VITE_API_URL=http://127.0.0.1:8020 VITE_CHAIN_ID=84532 VITE_VAULT_ADDRESS=0x558e8E8b2E20D41cE763A2c0FdC1d2c8A5B34FC5 VITE_RPC_URL=https://sepolia.base.org VITE_EXPLORER_URL=https://base-sepolia.blockscout.com VITE_DEV_SIGNING=0 npx vite --port 5174`.
  4. `.venv/bin/python scripts/trustee_session.py raise`: the posture goes to 1, so the next routine payout waits for a trustee.
  5. At http://127.0.0.1:5174, as Finance Officer: "Pay household ZKT-H14 this month.", then Confirm. The payout shows Waiting for a Trustee.
  6. Switch to Trustee, Connect MetaMask, check the decoded fields against the summary, Sign in MetaMask. The row turns Paid with a Blockscout link.
  7. `.venv/bin/python scripts/trustee_session.py lower`, then commit `evidence/sepolia-trustee/` (its `*.log` files are ignored).

- **The red team's variants (decision E-41), 20 October.** Registered in `redteam/protocol-variants.md` before the draw. Each stage, from the run copy:

  ```bash
  .venv/bin/python -m redteam.variants block --at 2026-10-19T23:40:00Z       # the stage's block, after its time
  .venv/bin/python -m redteam.variants sample --stage 1 --block <n> --block-hash <hash>
  (set -a && . ./.env && set +a && .venv/bin/python -m redteam.variants run --stage 1)
  .venv/bin/python -m redteam.variants bounds --run-id variants-stage1
  ```

  Stage 2 is the same with `--stage 2` and `--at 2026-10-20T01:40:00Z`; it runs only if it can finish by 13:00 in Kuala Lumpur, whatever stage 1 showed.

## 9. Documents (2 hours)

```bash
git apply docs/patches/readme-e4-fills.patch && git commit -am "Apply the README audit's fixes"   # done, 5c3a974
.venv/bin/python scripts/fill_readme.py          # done 19 October; it now reads README.md and lists what is left
.venv/bin/python scripts/build_deck.py --pdf --team "Amanah" --members "Abdul Hafiz Bin Mohd Noor Azman, Muhammad Khaidhir Bin Mohd Razin"   # done 19 October
```

Then by hand:
- the markers `fill_readme.py` lists as left: the team and members, the video and deck links, the team's details and the supervision line (the pilot outreach and the reading of the results are done);
- the README's USDC rows: the demo token's address, and why it is not Circle's (decision A-12); done, `ac98680`;
- the README's hard-coded Basescan links, such as the vault's address row: Blockscout, where the source is verified (decision A-13); done, `ac98680`;
- the status lines at the top of `docs/technical-documentation.md` and `docs/security-self-assessment.md`; done, `ee5caed`;
- move `docs/submission-readme.md` into `README.md`; done, in the house style (decision E-23);
- read every deck slide against the README.

## 10. Package and send (1 hour)

```bash
.venv/bin/python scripts/presubmit.py --links --verify
```

Done when it prints no FAIL. Then work through its `todo` lines, in this order:
1. with Hafiz's go, fast-forward `main` to `lane/release`: `git checkout main && git merge --ff-only lane/release && git push origin main`. This is the merge in the order A to E; checked on 19 October in a throwaway worktree: `main` is an ancestor of `lane/release`, which already holds every lane, merged in the order A and B, C, D. Merging lane by lane from `main` instead stops at lane C on a `docs/decisions.md` conflict that `lane/release` resolved on 18 October;
2. re-author the cloud session's commits and force-push once, with Hafiz's go at that moment (decision E-18). Then, in the clone where filter-repo ran: `.venv/bin/python scripts/rehash_refs.py --map .git/filter-repo/commit-map --dry-run`, read the list, run it again without `--dry-run`, run `bash scripts/reproduce.sh`, and commit and push "Commit references point at the rewritten history" (decision E-38). Only then seal the submission (`scripts/seal.py`, decision E-36), since the seal hashes the files. Every other clone is cloned again;
3. make the repository public, and open every link from a logged-out browser;
4. put the video and deck on OneDrive;
5. send the deliverables email (the draft is kept outside the repository, beside the registration email) before Tuesday 20:00.

## 11. The 20 October runs (done; to repeat them)

- **No model from outside China** (decision E-30). One run swaps the planner without editing `.env`:

  ```bash
  (set -a && . ./.env && set +a && PLANNER_PROVIDER=openai PLANNER_MODEL=kimi-k3 PLANNER_LINEAGE=moonshot/kimi \
    PLANNER_BASE_URL="$DASHSCOPE_BASE_URL" PLANNER_API_KEY="$DASHSCOPE_API_KEY" \
    .venv/bin/python scripts/run_demo.py --network anvil --live)        # writes evidence/anvil-demo/; the committed run is evidence/domestic-anvil/
  ```

  The same variables run the red team: `.venv/bin/python -m redteam.run --config redteam/configs/domestic.yaml --anvil --run-id <new id>`, and the Chinese set: `.venv/bin/python -m redteam.zh --run --run-id <new id>`.
- **FISCO BCOS** (E-31): `bash scripts/reproduce.sh --fisco` builds a one-node chain, deploys the fixture and runs the five checks. `FISCO_DIR` picks the folder; the default is `~/fisco`.
- **ERC-8004** (E-32): `python scripts/register_agents.py --check` reads the three agents back; without `--check` it registers whatever `evidence/erc8004.json` lacks.
- **Slither and coverage** (E-33): the commands are at the top of `docs/static-analysis.md`.
- **Everything a reviewer can check without a model key:** `bash scripts/reproduce.sh --chain --fisco`, then the rows of `docs/claims.md`.
- **The two PDFs** (E-37), after any change to their Markdown: `uv run --with markdown==3.7 python scripts/docs_pdf.py . /tmp/amanah-pdf`, then `NODE_PATH=frontend/node_modules node scripts/docs_pdf.js /tmp/amanah-pdf docs`. Look at the pages before committing.
- **The variants' companion and repeats** (E-45): `.venv/bin/python -m redteam.variants run --set legit` and `.venv/bin/python -m redteam.variants repro`, each inside `(set -a && . ./.env && set +a && DAILY_MODEL_CALL_CAP=1600 ...)` on a day whose counter is already high.

## 12. The hosted demo and the voiced video (20 October afternoon)

- **The hosted demo** (E-43): `bash scripts/build_demo.sh <commit> /mnt/c/<a Windows folder>`, then in the printed stage folder, from Windows: `VERCEL_ORG_ID=<team id> VERCEL_PROJECT_ID=<project id> npx vercel@64.7.0 deploy --prebuilt --prod --yes` (the ids are in the Vercel dashboard of the `amanah-demo` project). Check that `https://amanah-demo.vercel.app/version.txt` names the commit, then run the committed browser tests against it with a Playwright config whose `baseURL` is the demo and which starts no server.
- **The voices** (E-44): Hafiz and Khaidhir record into the project folder's `submission/voice/raw/`, either one file per line and take, or each speaker's lines in one take with three seconds between lines (`hafiz-all.m4a`, `khaidhir-all.m4a`), which the cut splits on the pauses and matches to the lines by what was said (a line said twice keeps its last try). The recording sheet is `submission/voice/Recording Script.pdf`, generated from `docs/video/script-v2.md`.
- **The voiced cut**, from the run copy in WSL, about ten minutes a pass:

  ```bash
  W=/mnt/c/<a Windows folder>/video-work          # Windows' ffmpeg needs the work folder on a Windows drive
  .venv/bin/python docs/video/dialogue.py --raw /root/amanah-video/take4 --voice "<project folder>/submission/voice/raw" \
    --takes "<project folder>/submission/voice/takes.md" --work $W --out $W/amanah-demo.mp4 --plan   # timing only
  .venv/bin/python docs/video/dialogue.py ... --out $W/amanah-demo.mp4                                  # the render
  ```

  With Hafiz's MetaMask capture: `--metamask FILE --metamask-span a,b --metamask-mark paid=SECONDS`. For the 20 October capture (`submission/w34/w34.mp4` in the project folder, 1920 by 1080): `--metamask-span "64.3,67.2;74.8,79.5;88.3,93.3" --metamask-mark paid=75.0`, which keeps MetaMask's Signature request and the Confirm click, the Trustee page's Paid row, and Blockscout's Success. The render writes the 1080p MP4, a 720p copy and the captions (`.srt`). Without the voices, `docs/video/cut.py` still makes the captions-only cut. `--acts 3,5` renders only those acts, for a quick look.
- **The mirror for mainland China** (E-48): `BASE=/amanah-wallet/ bash scripts/build_demo.sh <commit> /tmp` prints a pages folder; commit it as an orphan `gh-pages` branch (`git init -b gh-pages` in a copy, one commit, push to the repository's `gh-pages`). GitHub Pages serves it at https://hafizmnazman.github.io/amanah-wallet/; its `/version.txt` names the commit.
- **The README's four GIFs** (E-47): `.venv/bin/python docs/video/gifs.py --raw /root/amanah-video/take4 --work /mnt/c/<a Windows folder> --out .github/readme/gifs`.
- **After the re-authoring** (E-48): every push goes to `lane/release` and to `main` (`git push origin lane/release && git push origin lane/release:main`); an old hash cited anywhere maps to its new one in `docs/commit-map.txt`.
