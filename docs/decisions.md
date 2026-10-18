# Decisions

Choices the plan left open, and changes to the shared interfaces in plan section 3. Each lane adds its own section. The newest entry in a section goes last.

## Lane A: contracts

**A-1. The interface is as the plan wrote it.** `contracts/src/IAmanahVault.sol` matches plan section 3.2: every function, event, struct and error name. Everything below is either added to the contract alone or settles a point the plan left open.

**A-2. Five errors added to the contract, not the interface.**

| Error | When |
|:--|:--|
| `ZeroAddress` | A zero USDC, trustee, guardian, signer or beneficiary address |
| `InvalidRole` | `registerSigner` with role `NONE` |
| `InvalidVerdict` | `anchorDecision` with verdict `NONE` |
| `NotChecker` | `anchorDecision` from a key that is not an active planner, auditor or sentinel |
| `TooFewTrustees` | `setSignerActive` would leave fewer than two active trustees, which would make governance impossible |

**A-3. Which plan error fires where the plan left a choice.**
- A governance signature from an inactive trustee gives `InactiveSigner`, and from any other key `NotTrustee`.
- Fewer than two trustee signatures gives `QuorumIncomplete`.
- A guardian or posture oracle signature inside a payout quorum also gives `QuorumIncomplete`.
- `setMandate` with `cap` above `hardCeiling` gives `AboveHardCeiling`.
- `cancelBeneficiary` from anyone but an active trustee or the guardian gives `NotTrustee`. For a wallet that is not allowlisted it gives `NotAllowlisted`.

**A-4. Overrides.**
- `executeOverride` accepts only a refusal anchored by a key registered as AUDITOR or SENTINEL. This follows the tier 3 row of the submission README.
- Each refusal can be cited once.
- An override keeps every hard limit: allowlist, cooling-off, mandate, hard ceiling, daily budget and per-beneficiary cap. It skips only the cap, the 80% line and the posture.
- `PayoutExecuted` reports tier 3 for an override. `tierOf` never returns 3.

**A-5. Registry.**
- `registerSigner` refuses a key that already has a role. To rotate a key, register the new key, then deactivate the old one.
- `registerSigner` can register trustee and guardian keys, so two trustees can replace a third.
- The evidence view is stored and emitted, but not enforced.

**A-6. Mandate expiry.** A mandate stops working once `block.timestamp` passes `expiry`. Nothing treats an expiry of 0 as "never".

**A-7. Additions to the contract's ABI.**
- Views: `hashGovernance`, `spentThisPeriod`, `nonceUsed`, `govNonceUsed`, `refusalUsed`, `activeTrustees`, `lastReportHash`, `postureChangedAt`, `usdc` and `coolingOff`.
- Constants: the action hashes, the type hashes, the tiers, `ROUTINE_SHARE_BPS` and `PERIOD`.

They are for lane B's chain client and `GET /api/posture`. `shared/abi/AmanahVault.json` holds the full ABI.

**A-8. Environment names.**
- The deploy script reads `USDC_ADDRESS` from `.env.example`. Plan task A5 calls it `USDC`.
- Trustee and guardian addresses come from `TRUSTEE1` to `TRUSTEE3` and `GUARDIAN` when set. Otherwise they are derived from the matching `_KEY` variables. This lets a trustee whose key lives only in MetaMask be named.
- `COOLING_OFF` (default 600 seconds) and `CONTROL_AUDITOR_KEY` are new, and are listed in `.env.example`.

**A-9. Fixture data.** The format lane C writes for the fixture is fixed in `shared/fixture-data.md`. Until lane C's files exist, the fixture reads samples in `contracts/test/fixtures/`. The Anvil fixture also registers a Claude-lineage control auditor, so scenario 11 can be driven on Anvil.

**A-10. Open: scenario 7 conflicts with the flood relief mandate.** Plan section 10 gives `REL-PERAK-FLOOD` a per-beneficiary cap of 600 USDC. Scenario 7 pays one beneficiary 1,200 USDC, which reverts with `BeneficiaryCapExceeded` before any trustee can co-sign. `contracts/test/Scenarios.t.sol` shows both outcomes. Two fixes, for Hafiz to choose:
1. Raise that per-beneficiary cap to 1,500 USDC, below the 2,000 hard ceiling, and keep the 1,200 grant. Nothing else depends on the 600.
2. Lower the grant to between 301 and 600 USDC. It is still above the 300 cap, so still elevated.

Until a choice is made, the samples in `contracts/test/fixtures/` keep the plan's 600.

**A-11. Scenario 13 depends on scenario 6.** The second 199 USDC payout crosses the 80% line only if scenario 6 paid more than 1,602 and at most 1,801 USDC that day. The third payout hits `BeneficiaryCapExceeded` only if a trustee co-signed the second one first. Details are in `shared/fixture-data.md`.

## Lane B: agent wallet backend

**B-1. A standalone backend package.** Amanah's backend, spending control, durable write queue and session layer are not in this repository (see `docs/PATHS.md`). So lane B stands alone in `backend/app/agentwallet/`, with three stand-ins:
- `DAILY_MODEL_CALL_CAP` in `models.py` for the spending control;
- a SQLite store in `queue.py` for the durable write queue, plan tasks B3 and B9;
- the `X-Amanah-Role` and `X-Amanah-User` headers in `roles.py` for the session and role checks, as agreed with lane D.

Each stand-in sits behind one function, so it can be swapped for Amanah's own when the code moves.

**B-2. The books are a JSON file.** `books.py` reads lane C's `redteam/data/books.json` and writes executed payouts to a ledger in the state directory. The auditor's integrity check compares each record with its sha256 in `books_anchor.json`. That file stands in for the plan's on-chain or evidence-pack anchors. A payout the ledger recorded from the chain is anchored by its `PayoutExecuted` event instead.

**B-3. Additions to the API in plan section 3.3.** None changes an existing shape:
- `ChatRequest.programme_code`, optional, from lane D's fund selector. It is accepted and not used yet, so the demo's clarifying question stays.
- `GET /api/agent/payouts/{proposal_id}`, the status poll lane D asked for.
- `GET /api/alerts`, the trustee alerts of plan task B9.
- `GET /api/health`, which the scripts wait on.

**B-4. A fourth verdict, UNAVAILABLE.** Plan task B5 says a checker that cannot answer returns `{"verdict": "UNAVAILABLE"}`. So `Verdict.verdict` in API responses can be `UNAVAILABLE`, and the payout is then `queued`. Lane D's types list three values and should add this one.

**B-5. Amounts come from the books in the product.** The planner graph resolves every registered beneficiary's amount from the books (`strict_books_amounts=True`). The planner-alone path that red-team configuration S1 uses keeps the model's own amounts. S1 then measures what a typical single-model agent wallet would sign.

**B-6. Model names, prices and fallbacks come from the environment.** The code names no model:
- Prices come from `<ROLE>_PRICE_PER_MTOK="in,out"`. With it unset, cost is not recorded.
- Claude requests ask for server-side refusal fallbacks by default. A model that does not take them answers 400, and the client stops asking for that model.
- `PLANNER_REFUSAL_FALLBACK=off` turns fallbacks off. The red-team runs set it, so each measured reply comes from the model named in `.env`.

**B-7. Dry-run mode.** With no key for a role, or with `AGENTWALLET_DRY_RUN=1`, each caller answers from its own deterministic rules:
- the planner: `offline_understand`;
- the auditor: `offline_judgement`;
- the reader: patterns;
- the correction node: `offline_correction`.

The reply's model is `dry-run:<role>`, so a dry-run result cannot pass for a live one. The sentinel never calls a model.

**B-8. Checkers anchor their own refusals.** On REJECT or ESCALATE, the auditor and the sentinel call `anchorDecision` with their own keys when `RPC_URL` is set. A trustee override can then cite the anchor. The planner never anchors a refusal for them.

**B-9. Posture thresholds.** `posture.py` raises the posture to 1 above 10% joint failure of planner and auditor, and to 2 above 25%, as plan task C6 fixes. It reads `joint_failure_planner_auditor` from the newest `redteam/results/<run_id>/summary.json`. `POSTURE_THRESHOLD_1` and `POSTURE_THRESHOLD_2` lower the thresholds for the demo cycle of plan task C8. The module never lowers the posture: that takes two trustees.

**B-10. The trustee summary's format.** `reporter.summary` writes the amount first with thousands separators, as in "Pay 1,200.00 USDC". It keeps up to 6 decimals, so the text never rounds away part of the signed amount. It names the beneficiary wallet in full. Lane D's trustee page parses both back and blocks signing on a mismatch.

**B-11. Chain tests are isolated.** Each test that uses the Anvil fixture runs between `evm_snapshot` and `evm_revert`, so no test depends on another's spend or posture.

**B-12. A gas margin over the node's estimate.** On Anvil, about 1 transaction in 40 ran out of gas with the estimated limit, though a replay of the same call succeeded. The posture test's `lowerPosture` showed it. `chain.py` now sends 1.25 times the estimate. Base Sepolia charges only for gas used, so the margin costs nothing. Calls expected to revert still use the fixed 1,000,000 limit.

**B-13. Recurring payouts are drafts.** A programme's `schedule` in the books, `{"kind": "monthly", "day_of_month": 5}` for the zakat programme, makes `recurring.py` draft that month's batch from the books on or after that day. It needs no model call. The API runs the job at start and every `SCHEDULE_SECONDS`, default 3,600, for the officer in `SCHEDULE_OFFICER`. Set `AGENTWALLET_SCHEDULE=0` to turn it off. The draft waits in `GET /api/agent/scheduled` until the officer confirms it. Nothing is ever confirmed by the job.

**B-14. A GPT auditor for the red team only.** The `auditor_gpt` role uses `AUDITOR_GPT_MODEL` with `OPENAI_API_KEY`, lineage `openai/gpt`. It fills the third lineage of the joint-failure matrix in plan task C5. No key for it is registered in the vault, and the product never asks it for a verdict.

**B-15. The usage report is public and holds sums only.** `GET /api/usage` totals the books' payout history and the executed payouts by fund, programme and month (`usage.py`). It names no recipient and shows no wallet or reference. A month with fewer than 3 payouts shows its count but not its sum, so one household's amount cannot be read off it. It needs no role, because donors and the public are its readers (README section 3).

**B-16. Model errors fail closed.** The plan's live runs will be the first, so every model answer that cannot be used becomes a designed outcome rather than an error:
- **A reply cut off or not valid JSON.** It counts as an answer outside the schema. The planner asks the officer to rephrase, the auditor escalates, and the reader keeps its pattern flags.
- **An API error, 4xx or 5xx.** It counts as unavailable, with the status and message in the reasons. The auditor's failover then tries its next Qwen model, and the payout is queued if none answers.
- **A reference the books do not have.** It resolves to an empty plan.

**B-17. The sentinel reads payout history from the vault.** With `RPC_URL` and `VAULT_ADDRESS` set, `sentinel/judge.py` takes a household's past payouts from the books' own history plus the vault's `PayoutExecuted` events for that programme and wallet. It reads today's spend from the vault's `spentToday`, not from the planner's request. The backend's ledger file no longer feeds the frequency, structuring and budget rules, so a lost `backend/var/` cannot hide a recent payout.
- **Reading.** The events are read once from the deployment block, then only new blocks. The start is `VAULT_FROM_BLOCK`, else the block in `contracts/deployments/<chain id>.json` when that record is for this vault, else block 0 on Anvil. A changed hash at the last block read, from a reorg or an Anvil snapshot revert, starts the read again.
- **Failing closed.** If the vault cannot be read, the sentinel answers UNAVAILABLE and the planner queues the payout. On a public chain with no known deployment block it does the same, rather than scan from block 0.
- **The red team is unchanged.** Arm S4 still calls `rules.assess` with the books and the ledger, so cached runs stay comparable.
- **A rerun on the same chain meets its earlier payouts.** Even with a fresh state directory, the frequency rule now refuses a monthly payout to a household the vault paid in the last 25 days.

**B-18. Evidence appends hold a file lock.** The API, the auditor and the sentinel run as separate processes, and `scripts/dev_up.sh` gives them one evidence folder. `ActionLog.append` read the last record and wrote the next under a lock that only held within one process. Six processes appending at once broke the hash chain at line 2. Each append to `action-log.jsonl` or `transactions.csv` now holds an exclusive `flock` on the file, so processes write in turn and only one writes the CSV header. Windows has no `fcntl`, so there the lock holds within one process only. `test_separate_processes_append_in_turn` runs six processes against both files.

**B-19. The usage report reads the vault's events too.** `GET /api/usage` counted on-chain payouts from the backend's ledger, so an API started with another state folder than the demo's, as on Base Sepolia, showed none of the demo's payouts. With a vault configured, `usage.report` now takes them from `PayoutExecuted` events, with the books' history beside them, as the sentinel does (B-17). If the vault cannot be read, the report falls back to the ledger rather than fail, because it is a public page. A new field, `source`, says which it used.

**B-20. Fixes from the review of 18 October.** A second Claude session reviewed the day's backend changes and reproduced five faults on Anvil. Each fix has a test that failed before it:
- **The sentinel service trusted a caller's `features`.** A request carrying them was approved and signed on the caller's numbers, even after an on-chain payout that the sentinel's own history refuses. The service now ignores `features` and always works its numbers out itself (`test_the_service_ignores_a_callers_features`). The field stays in the request, as plan section 3.4 has it.
- **The event cache had no lock.** Concurrent verdicts, which uvicorn's thread pool and the queue's retry loop both produce, could duplicate cached payouts or lose them for good. Reads now take a lock, and a read changes the cache only when it completes (`test_concurrent_reads_neither_duplicate_nor_lose_payouts`).
- **Unavailable reasons carried the RPC URL.** Providers put API keys in that URL's path, and the reasons reach the queue, the officer's screen and the evidence. A chain error now names only its type (`test_unavailable_reasons_never_show_the_rpc_url`).
- **`VAULT_FROM_BLOCK` was trusted blindly.** A start after the chain's head gave an empty history and an approval. The deployment record now comes first, the variable is ignored on Anvil, and a start after the head is refused (`test_vault_from_block_cannot_hide_payouts`).
- **Any RPC error halved the log range for good.** A burst of node errors could leave one block per request, too slow to answer. Only a refused range or result size halves it now; other errors fail that one read, and the queue retries it (`test_a_node_error_fails_one_read_without_shrinking_the_range_or_losing_payouts`).
