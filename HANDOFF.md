# Handoff

The cloud session's record of what is built, what needs Hafiz, and what comes next. A new session reads this first, then `CLAUDE.md`, then `IMPLEMENTATION_PLAN.md`. Each lane's own notes are in `docs/handoff/lane-<letter>.md`.

Last updated: Sunday 18 October 2026, 22:20 Malaysia time. The deadline is Tuesday 20 October, 23:59; the plan wants the email sent before Tuesday 20:00.

## Start here

**Continue from `lane/release`.** It has every lane merged, and its copies of `HANDOFF.md`, `docs/PATHS.md` and `docs/decisions.md` are the current ones. The lane branches' copies of those docs are older snapshots. `docs/runbook.md` lists the remaining steps as commands, in order, from the keys to the email.

```bash
git fetch origin
for b in contracts backend redteam frontend release; do git branch --track "lane/$b" "origin/lane/$b" 2>/dev/null; done
git checkout lane/release && git submodule update --init --recursive
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt    # the backend's and red team's pins, and python-pptx
(cd frontend && npm ci)
```

Anvil and forge must be on PATH; Foundry 1.7.1 was used. Then check that everything still passes. These exact commands were run from a fresh clone of `lane/release` on 18 October, at 22:15 Malaysia time, and gave the counts below:

```bash
(cd contracts && forge test)                                   # 109
(cd backend && ../.venv/bin/python -m pytest)                  # 117, plus 4 live tests that skip without keys
.venv/bin/python -m pytest -c redteam/pytest.ini redteam/tests # 24
.venv/bin/python -m pytest -p no:cacheprovider scripts/tests   # 18
(cd frontend && npm run build && npm test && npx playwright test)            # build, 23, 14
(cd frontend && PYTHON=../.venv/bin/python npx playwright test --config playwright.stack.config.ts)  # 3
.venv/bin/python scripts/run_demo.py --network anvil           # 16 of 17; scenario 7 waits on A-10
```

## Branches

| branch | what it holds |
|:--|:--|
| `lane/release` | every lane merged, plus lane E's scripts. Continue here |
| `claude/loving-faraday-x5olmb` | the cloud session's own branch, kept equal to `lane/release` |
| `lane/backend` | lane A, lane C's data (C1), and lane B's backend |
| `lane/redteam` | lanes A and B, plus lane C's harness |
| `lane/frontend` | lane A, plus lane D's frontend |
| `lane/contracts` | lane A |
| `main` | untouched since the first commit. Lanes merge into it in the order A, B, C, D, E, which needs Hafiz |

Every lane branch was merged into `lane/release` with merge commits. No history was rewritten and nothing was force-pushed. `gitleaks detect` found no leaks before each push.

## Needs Hafiz

In the order they block things:

1. **Decision A-10, scenario 7's numbers.** The 1,200 USDC flood grant is above the flood relief per-beneficiary cap of 600 USDC. So the vault refuses it with `BeneficiaryCapExceeded` before a trustee can sign. It is the only scenario that fails in the demo run.
   - Recommended: raise that cap to 1,500 USDC. This is ready as a tested patch: `git apply docs/patches/a10-flood-cap-1500.patch`, then commit. With it, the demo passes 17 of 17 (`docs/patches/README.md`).
   - Alternative: a grant between 301 and 600 USDC.
   - Details: `docs/decisions.md` A-10.
2. **`INSTITUTION_HMAC_KEY`, then regenerate the data.** The beneficiary id hashes use a development key for now. Set the real key in `.env` and regenerate the data. Do it together with A-10, and before item 3, because the deploy registers these hashes on-chain.
3. **Deploy and verify the vault on Base Sepolia (task A6).** The cloud network blocks Base Sepolia and Etherscan, so run it locally:
   ```bash
   cd contracts
   (set -a && . ../.env && set +a && forge script script/Deploy.s.sol --rpc-url base_sepolia --broadcast --verify)
   ```
   - It needs `RPC_URL` and `BASESCAN_API_KEY`.
   - It needs `TRUSTEE1` to `TRUSTEE3` and `GUARDIAN`, as addresses or keys.
   - It needs `RELAYER_KEY` with about 0.01 Base Sepolia ETH. The deploy uses 3,377,006 gas.
   - Afterwards, commit `contracts/deployments/84532.json` and the 84532 broadcast file.
4. **Test USDC on Base Sepolia.** The demo deposits 5,000 USDC and pays out about 3,700 USDC (`docs/handoff/lane-e.md`). Check how much the Circle faucet gives. If it is far less, decide: lower the demo's amounts, or deploy MockUSDC on Base Sepolia, which changes `USDC_ADDRESS` in plan section 9.
5. **Gas for the signers.** On Base Sepolia, these keys send transactions and need a little ETH:
   - the relayer;
   - the auditor and the sentinel, for refusal anchors;
   - the posture oracle;
   - the guardian;
   - the planner, for scenario 12;
   - the donor.
6. **Model keys and names in `.env`.**
   - Planner: `ANTHROPIC_API_KEY` and `PLANNER_MODEL`.
   - Auditor: `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL` and `AUDITOR_MODEL`.
   - Red team: `OPENAI_API_KEY`, `REDTEAM_MODEL`, and `AUDITOR_GPT_MODEL` for the matrix's third lineage.
   - Prices: `<ROLE>_PRICE_PER_MTOK`, for the red team's cost column.

   The code names no model. Nothing has run live yet. Then run `cd backend && python -m pytest -m live`: four small paid calls, one per model role.
7. **Server-side refusal fallbacks are on by default.** Claude requests ask for them, so a refused request may be answered by another model, and the reply names it. Set `PLANNER_REFUSAL_FALLBACK=off` for red-team runs. The protocol asks for it, so each measured reply comes from the model named in `.env`.
8. **The red team's attack seeds (C2) and the mutation agent (C3).** The cloud session's red-team worker was stopped by the model provider's safety classifier, category "cyber". So this session wrote no attack text.
   - 28 unreviewed draft seeds are in `redteam/gallery/drafts/`. They are not loaded until a person reviews them and moves them up one folder.
   - Still to write: the rest of the 40 seeds, among them the `encoded`, `data_extraction`, `privilege_escalation` and `structuring` classes.
   - Still to build: `redteam/mutate.py`, which `run.py` and `immune.py` already expect.
9. **The red-team protocol (C6).** Fill the model names and case counts in `redteam/protocol.md` and commit it before the full run. Then put that commit's hash in the README.
10. **A MetaMask trustee for D3.** Use an account registered as one of `TRUSTEE1` to `TRUSTEE3`, with a little Base Sepolia ETH. Then set `VITE_VAULT_ADDRESS` and `VITE_CHAIN_ID=84532` in `frontend/.env.local`.
11. **Where the product lives.** This repository's backend and frontend stand alone. Amanah's backend, session layer, write queue and Vite app are not here. Decide whether the demo ships these, or moves them into Amanah. Each stand-in sits behind one function (decision B-1, `docs/handoff/lane-d.md`).
12. **Check two scenario readings.**
    - Scenario 9's REJECT comes from the sentinel's frequency and structuring rules: the household was paid hours earlier, in scenario 6 (decision E-4).
    - Scenario 14 uses a summary labelled as fabricated for the demo when no real red-team result is above the threshold (E-5).
13. **The project licence (E6).** The submission gate fails until a `LICENSE` is committed. MIT matches the `SPDX-License-Identifier: MIT` already in every Solidity file: `git apply docs/patches/licence-mit.patch`.
14. **Commit identity.** Commits from the cloud session are authored as `Claude <noreply@anthropic.com>`, the container's git identity. CLAUDE.md asks for no AI credit in messages; decide whether the author field matters too.

## What is built

| lane | done | not done | notes |
|:--|:--|:--|:--|
| A contracts | A1 to A5 | A6, the Base Sepolia deploy | `docs/contract-tests.md` |
| B backend | B1 to B11, in dry-run | live model runs | `docs/handoff/lane-b.md`, `docs/api.md` |
| C red team | C1; C2's format and legitimate set; C4, C5 with the GPT signer, C6 draft; C8 without mutation | C2's seeds, C3 mutation, C7 full run | `docs/handoff/lane-c.md`, `redteam/protocol.md` |
| D frontend | D1 to D6, standalone | D3's MetaMask run on Base Sepolia; moving into Amanah | `docs/handoff/lane-d.md` |
| E release | dev stack, E1 on Anvil, E2 tools, browser checks on the real stack, E3 drafts, E4's fixes as a patch, E5's deck builder, split screen and shot list, E6's gate and email draft | the Base Sepolia run, E3's numbers, E4 to E6 with real numbers, the video | `docs/handoff/lane-e.md` |

What works end to end today, on Anvil, in dry-run:
- **The officer's conversation.** It pays 11 households through the separate auditor and sentinel services and the vault: in the browser, over HTTP and from the demo script.
- **An elevated payout.** It waits for a trustee, and the trustee page signs and pays it.
- **Refusals.**
  - An induced transfer is refused, and both checkers anchor their refusals.
  - A prompt-injected letter is flagged, and the second payout it asks for is refused and anchored.
  - Forced, same-lineage and planner-governance attacks are mined and reverted with the vault's errors.
- **Structuring.** It is stopped at the per-household cap.
- **The sentinel's history.** It counts the vault's own payout events, so a lost state directory cannot hide a payout made earlier (decision B-17).
- **One evidence chain across processes.** The API, the auditor and the sentinel append to one hash-chained log under a file lock (decision B-18). Before the fix, six concurrent writers broke the chain at line 2.
- **The immune loop.** It raises the posture, and two trustees lower it again.
- **An override.** It cites an anchored refusal.
- **A pause.** It blocks payouts until two trustees unpause.
- **Evidence.** Every transaction is tagged in `transactions.csv`. The action log is hash-chained, and its head is anchored on-chain. `verify.py` re-checks every executed payout from the chain.
- **The red-team pipeline.** It runs S1 to S5 with a paired cache and writes a report with Wilson intervals, McNemar tests and the joint-failure matrix.
- **Recurring payouts.** The books' monthly schedule drafts the zakat batch as a plan card. It shows on the officer page above the chat, and only the officer confirms it (plan task B11).
- **How each fund was used.** A public page and route give totals by programme and month, with no recipient and no wallet (decision B-15).

## Test results, 18 October 2026

| suite | command | result |
|:--|:--|:--|
| contracts | `cd contracts && forge test` | 109 passed: 86 unit and fuzz, 2 vector, 13 scenario, 8 invariant |
| backend | `cd backend && python -m pytest` | 117 passed, 4 live skipped; 17 of them start Anvil |
| red team | `python -m pytest -c redteam/pytest.ini redteam/tests` | 24 passed; 1 starts Anvil |
| release scripts | `python -m pytest -p no:cacheprovider scripts/tests` | 18 passed; 2 start Anvil |
| frontend unit | `cd frontend && npm test` | 23 passed |
| frontend browser, mock | `cd frontend && npx playwright test` | 14 passed |
| frontend browser, real stack | `npx playwright test --config playwright.stack.config.ts` | 3 passed |
| demo on Anvil | `python scripts/run_demo.py --network anvil` | 16 of 17 checks; scenario 7 waits on A-10 |
| secrets | `gitleaks detect` | no leaks |

## Known gaps and incidents

- **No live model call has run.** Every model result so far is dry-run. The dry-run planner follows explicit transfer requests on purpose, so the checkers can be shown working; it is not a model.
- **Not built:**
  - E3's numbers, the README's final fill, the video, and the package;
  - the Amanah integration.
- **Drafted, waiting on the runs:** the deck (`docs/deck/`, built by `scripts/build_deck.py`), the video shot list (`docs/video-shot-list.md`) and the submission email (`docs/submission-email.md`).
- **A failing test was pushed once.** On `lane/backend`, commit `453c361` went out while a chain test failed about one run in three. The command chain checked `tail`'s exit code instead of pytest's. The cause was gas estimates that sometimes left too little room on Anvil. Commit `1974068` fixed it (decision B-12). Afterwards, 120 cycles of the failing sequence passed, as did 10 runs of the test file.
- **Closed: the sentinel's history was off-chain.** It read payout history from the books and the backend's ledger in `backend/var/`, so a lost ledger hid recent payouts. It now counts the vault's `PayoutExecuted` events for the household and reads `spentToday` itself, and answers UNAVAILABLE when it cannot read the vault (decision B-17). The red team's S4 arm still uses the books and the ledger.
- **Cloud network limits.** The cloud network blocks Base Sepolia RPCs, Etherscan, and the Qwen and OpenAI hosts. Anything that needs them was left for the local session.

## For the README (task E4)

`docs/readme-audit.md` checks `docs/submission-readme.md` against the build. 17 claims did not match the repository, among them the test counts from Amanah's suites, folders that do not exist, a contract excerpt that has drifted, the on-chain books anchor and ERC-8004. One, the "how the fund was used" page, has since been built. The markers it can answer, and the corrected sections, are ready as `docs/patches/readme-e4-fills.patch` for Hafiz to read and apply. `bash scripts/test_all.sh` is the "one command" the README asks for.

## Next steps, in order

1. Pull `lane/release` and run the checks above.
2. Hafiz decides items 1, 2 and 4 above; then deploy on Base Sepolia (item 3). Before each paid step, `python scripts/preflight.py --stage deploy` (then `demo`, `models`, `redteam`) names what is still missing, with the item that fixes it. It sends nothing.
3. Put the model keys in `.env`. Run `pytest -m live`, then the demo on Anvil with live models: `python scripts/run_demo.py --network anvil --live`.
4. Red team:
   - write and review the seeds, and build `mutate.py`;
   - commit the protocol;
   - run `python -m redteam.run --config redteam/configs/full.yaml --anvil` live, into `redteam/results/final/`.
5. Run `python scripts/run_demo.py --network base-sepolia`, which starts the auditor and the sentinel as their own services, each with only its own key. Then `python scripts/verify.py --csv evidence/transactions.csv` and `python scripts/evidence_pack.py`. Commit `evidence/`.
6. Run the frontend against Base Sepolia with a MetaMask trustee, and record the video clips.
7. Fill E3's two drafts (`docs/technical-documentation.md`, `docs/security-self-assessment.md`) with the real numbers, finish E4's README with `docs/readme-audit.md`, then E5's deck and video and E6's package. After `git apply docs/patches/readme-e4-fills.patch` and the runs, `python scripts/fill_readme.py --readme docs/submission-readme.md --write` fills the markers the result files can answer, there and in E3's two documents: 77 of the README's 89 on a test with fabricated results, and every number in E3's two. Their status lines stay for Hafiz to rewrite. It lists the rest, which are Hafiz's: the team, the video and deck links, the pilot outreach, and the two sentences on what the results show.
8. Rebuild the deck with the real numbers: `python scripts/build_deck.py --pdf --team "..." --members "..."`. It prints what is still unfilled. Record the video from `docs/video-shot-list.md`; its opening is `python scripts/split_screen.py --live`.
9. Before the email, run `python scripts/presubmit.py --links --verify`. It must print no FAIL. Its `todo` lines are the steps no script can check, such as making the repository public. Today it fails 10 of 15 checks: everything that waits on the runs, the licence and the deck.
