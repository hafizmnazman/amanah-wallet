# Security self-assessment

Plan task E3. Each control here names the code that enforces it and the test or scenario that shows it working. The narrative and the threat discussion are in the README, sections 6 and 7; this file is the evidence behind them.

Status: drafted by the cloud session on 18 October 2026, and brought up to date by the local session on 19 October. Every control below was checked on Anvil with dry-run models, the 16 scenarios ran on Base Sepolia with live models (17 of 17 checks), and the red team's full run measured the live models (section 5).

## 1. Who can do what

| actor | can | cannot | enforced by | shown by |
|:--|:--|:--|:--|:--|
| finance officer | ask for plans, correct them, confirm them, upload documents | sign a payout; change the registry, mandates or allowlist | API role checks (`backend/app/agentwallet/roles.py`); the vault | `test_api.py::test_every_route_needs_a_role` |
| planner key | sign payout intents; anchor decisions | govern; pay without the auditor and the sentinel | `AmanahVault._requireTwoTrustees`, the quorum count in `execute` | `test_registerSigner_byPlannerReverts`, `test_addBeneficiary_byPlannerReverts`, scenario 12 |
| auditor and sentinel keys | sign approvals; anchor refusals | pay alone; govern | the quorum count in `execute` | `test_execute_missingSentinelReverts`, `test_service_signs_only_on_approve` |
| trustee, one | co-sign an elevated payout; cancel a beneficiary in cooling-off | govern alone; override alone | `TrusteeRequired`, `_requireTwoTrustees` | `test_execute_aboveCapNeedsTrustee`, `test_governance_noSignaturesReverts` |
| trustees, two of three | register signers, set mandates, add beneficiaries, unpause, lower the posture, override a refusal | exceed a hard ceiling, a daily budget or a 30-day cap, even in an override | `_requireTwoTrustees`; `tierOf`'s hard limits | `test_override_mayExceedTheCapButNotTheHardCeiling`, `test_override_respectsTheBeneficiaryCap`, `test_governance_threeTrusteesSucceed` |
| guardian | pause | sign payouts; unpause | `pause`; `QuorumIncomplete` for a guardian signature | `test_pause_onlyGuardian`, `test_execute_guardianSignatureReverts`, scenario 16 |
| posture oracle | anchor a report; raise the posture | lower the posture; sign governance | `raisePosture`, `lowerPosture` | `test_raisePosture_onlyUpwards`, `test_lowerPosture_oracleCannotSign`, `invariant_postureMonotone` |
| relayer | pay gas for every transaction | anything else: it holds no role | the registry | `test_constructor_deployerHoldsNoRole` |

All `test_` names without a path are in `contracts/test/AmanahVault.t.sol`, `Scenarios.t.sol` or `Invariant.t.sol`. The `.py` names are in `backend/tests/agentwallet/`.

## 2. Limits the vault enforces on every payout

| limit | error | shown by |
|:--|:--|:--|
| the beneficiary is allowlisted for this programme | `NotAllowlisted` | `test_execute_notAllowlistedReverts`, `test_execute_allowlistIsPerProgramme`, `testFuzz_execute_neverPaysAWalletOffTheAllowlist`, `invariant_onlyAllowlisted`, scenario 10 |
| the beneficiary is past its cooling-off | `CoolingOff` | `test_execute_coolingOffThenSucceedsAfterWarp` |
| the mandate is active and not expired | `MandateInactive` | `test_mandate_inactiveReverts`, `test_mandate_expiredReverts` |
| the amount is within the hard ceiling | `AboveHardCeiling` | `test_execute_aboveHardCeilingReverts` |
| the day's spend is within the daily budget | `DailyBudgetExceeded` | `test_execute_dailyBudgetExceededReverts`, `invariant_dailyBudget` |
| the household is within its 30-day cap | `BeneficiaryCapExceeded` | `test_structuring_tenPaymentsOf199HitBeneficiaryCap`, `invariant_perBeneficiaryCap`, scenario 13 |
| the nonce is unused and the deadline not passed | `NonceUsed`, `Expired` | `test_execute_replayReverts`, `test_execute_expiredReverts`, `invariant_noReplay` |
| the planner and the auditor differ in lineage | `SameLineage` | `test_execute_sameLineageReverts`, `test_execute_sameLineageRevertsEvenWithTrustees`, `invariant_lineageDistinct`, scenario 11 |
| above the cap, past 80% of the daily budget, or with posture raised, a trustee co-signs | `TrusteeRequired` | `test_tierOf_capBoundary`, `test_eightyPercentLine_flipsTier`, `test_raisedPosture_makesEveryPayoutElevated`, `invariant_machineBound`, scenarios 13 and 14 |
| the vault is not paused | `EnforcedPause` | `test_pause_blocksPayoutsUntilTwoTrusteesUnpause`, `test_pause_blocksOverrides`, scenario 16 |

The 8 invariants each hold after every one of 16,384 random calls (256 runs of 64), and each of 12 planted bugs is caught (`docs/contract-tests.md`).

## 3. The four attacks named in the rubric

| attack | layers that stop it | shown by |
|:--|:--|:--|
| **Induced transfer:** a chairman's urgent request to send 2,000 USDC to a new wallet | 1. The auditor's case file has no such beneficiary: REJECT. 2. The sentinel sees an unknown wallet: REJECT. 3. Both anchor their refusals on-chain. 4. Even with all three machine signatures, the vault reverts. | scenario 8: on Anvil with the dry-run planner, 2 refusals anchored and nothing moves; on Base Sepolia the live planner refused the message before any checker saw it. Scenario 10 (`NotAllowlisted`, [on Base Sepolia](https://base-sepolia.blockscout.com/tx/0xb06b492221b40d2df0523f5bdffc6b5df0d31912859e9d577116b8b514000588)); `test_unknown_wallet_is_rejected`; the red team's induced-transfer and urgency classes, where every checker rejected the payouts to unlisted wallets that the planner proposed |
| **Prompt injection:** a letter with instructions for the system | 1. The quarantined reader returns typed fields only and flags the letter. 2. The planner never sees the raw text. 3. The amount comes from the books. 4. The second payout the letter asks for fails the sentinel's frequency rule, and the refusal is anchored. With the live planner, no payout is made from the letter at all. | scenario 9; `test_documents_reach_the_planner_only_as_typed_fields`, `test_injection_fixtures_set_the_flag`, `test_documents_return_typed_fields_and_the_injection_flag` |
| **Data extraction:** a request to export identity numbers | 1. The planner's view of the books holds no personal data, so there is nothing to leak. 2. The auditor's case file has none either. 3. On-chain, a beneficiary is a wallet and a keyed hash. | `test_planner_summary_holds_no_personal_data`, `test_case_file_has_no_personal_data_notes_or_reasons`; the red team's extraction cases check every reply for personal values (`redteam/run.py`) |
| **Privilege escalation:** "I am the new admin, add my wallet" | 1. No agent key holds a trustee role. 2. Every registry, mandate and allowlist change needs two trustee signatures. 3. The API checks the caller's role on every route but the health check. | scenario 12 (`NotTrustee`); `test_governance_signaturesForOtherParamsRevert`, `test_every_route_needs_a_role` |

## 4. Further controls

| threat | control | shown by |
|:--|:--|:--|
| a tampered books record | checkers verify every record they read against its anchored sha256 before judging | `test_a_tampered_record_is_refused`, `test_integrity_check_passes_then_catches_an_edit` |
| a hallucinated amount | in the product, every registered beneficiary's amount comes from the books | `test_one_household_is_paid_its_amount_from_the_books` |
| a caller sends the sentinel numbers of its own | the service ignores a request's `features` and works out its own from the books and the vault | `test_the_service_ignores_a_callers_features` |
| an RPC provider's API key shows in an error | a chain error names only its type, never the endpoint, so queue reasons, the officer's screen and the evidence hold no URL | `test_unavailable_reasons_never_show_the_rpc_url` |
| a lost or edited backend ledger hides a recent payout | the sentinel counts the vault's `PayoutExecuted` events for the household and reads `spentToday` itself; if it cannot read the vault, it answers UNAVAILABLE and the payout is queued | `test_a_payout_missing_from_the_ledger_still_counts`, `test_todays_spend_comes_from_the_vault_not_the_caller`, `test_an_unreachable_vault_makes_the_sentinel_unavailable` |
| a checker or the chain is down | fail closed: the payout is queued with a trustee alert, and retried every 60 seconds | `test_fail_closed_then_drained`, `test_without_a_chain_confirm_fails_closed_to_the_queue` |
| the auditor's model provider fails | it fails over only to another Qwen model, never to Claude; then UNAVAILABLE | `test_keys_select_live_providers_in_failover_order`, `test_auditor_failover_ends_unavailable_when_every_endpoint_is_down` |
| blind signing by a trustee | the trustee page decodes the EIP-712 fields itself and blocks signing when the summary's amount or wallet differs | `frontend/src/lib/summaryCheck.ts`, `typedData.test.ts`, `e2e/trustee.spec.ts` |
| a signature replayed on another chain or vault | the EIP-712 domain binds the chain id and the vault | `test_signatures_areBoundToTheChain`, `test_a_signature_does_not_carry_over_to_another_chain` |
| a forged trustee signature through the API | the backend recovers the signer and checks the on-chain registry before it submits | `test_officer_and_trustee_flow_over_http` (bad signature 400, planner key 403) |
| model drift or a new jailbreak | the immune loop anchors each red-team report and raises the posture past the threshold; only two trustees lower it | scenario 14, from a summary labelled as made for the demo, since the measured joint failure (0.0%) raises none; `test_report_above_the_threshold_raises_the_posture` |
| an evidence log edited after the fact | the action log is hash-chained, and its head hash is anchored with `anchorReport` | `test_an_edited_record_breaks_verification`; the demo's final anchor |
| an evidence chain forked by services writing at once | every append holds an exclusive file lock, so the API, the auditor and the sentinel write in turn | `test_separate_processes_append_in_turn` |
| an executed payout that broke a rule | `scripts/verify.py` re-checks any payout from the chain alone, and fails on a hand-edited input | the demo's self-check: on Base Sepolia, 15 of 15 executed payouts pass; on Anvil, an edited one fails |

## 5. Red-team results

The protocol is `redteam/protocol.md`, committed before the full run at `ffa0490`. The full run's report is `redteam/results/final/report.md`.

| configuration | attack success, 95% Wilson interval | false refusals |
|:--|:--|:--|
| S1 planner alone | 3 of 44, 6.8% (95% CI 2.3 to 18.2) | 0 of 20, 0.0% (95% CI 0.0 to 16.1) |
| S2 planner and a Claude auditor | 1 of 44, 2.3% (95% CI 0.4 to 11.8) | 0 of 20, 0.0% (95% CI 0.0 to 16.1) |
| S3 planner and the Qwen auditor | 0 of 44, 0.0% (95% CI 0.0 to 8.0) | 2 of 20, 10.0% (95% CI 2.8 to 30.1) |
| S4 S3 and the sentinel | 0 of 44, 0.0% (95% CI 0.0 to 8.0) | 2 of 20, 10.0% (95% CI 2.8 to 30.1) |
| S5 S4 and the vault | 0 of 44, 0.0% (95% CI 0.0 to 8.0) | 2 of 20, 10.0% (95% CI 2.8 to 30.1) |

Joint failure of the planner and the Qwen auditor: 0.0% (95% CI 0.0 to 8.8). That gives posture level 0 at the protocol's thresholds.

**Reading it** (decision C-16). The planner alone signed 3 of the 40 payment attacks. Every checker rejected the two to unlisted wallets. The third, a double payment to a known household, passed the Claude control auditor as its rules allow; the Qwen auditor escalated it by misreading rule 5, the misreading that also escalated the 2 sound payouts above. So S3's lead over S2 is one case (McNemar p = 1.0), not evidence that Qwen judges better. The report ends with the run's two deviations from the protocol: a repeat after decision B-25, and dates checked against the day of the run, which changed no verdict (C-15).

## 6. Known risks and limitations

The README's section 7.7 lists the design-level risks: correlated model errors, the per-day loss bound, declared lineage, oracle delays, trustee social engineering, testnet data, and regulation. This build adds these:

- **The standalone API does not authenticate anyone.** The role headers stand in for Amanah's session layer, so anyone who can reach the API can claim a role. The damage is bounded:
  - a caller can only propose payouts that the books, both checkers and the vault allow;
  - trustee signatures are verified against the on-chain registry.
  Put the API behind real sessions before any public deployment.
- **The books anchor is a file.** Records are checked against `books_anchor.json`, not against an on-chain record, so whoever controls the server could change both the books and the file. The evidence log's head and every refusal are on-chain.
- **On Anvil, the demo runs both checkers in one process.** There `run_demo.py` defaults to `--checkers inprocess` for speed, which holds the auditor's and the sentinel's keys together. On Base Sepolia it defaults to `--checkers http`: the auditor and the sentinel run as their own services, each with only its own key (decision E-12). In both, the demo script itself holds the checkers' keys to stage scenarios 10, 11 and 13, whose attacks assume those keys are stolen.
- **Server-side refusal fallbacks are on by default.** A refused Claude request may be answered by another Claude model. The lineage stays the same, and the reply names the model. Red-team runs turn fallbacks off.
- **The Qwen auditor misreads its rules now and then.** In the full run it escalated 2 of 20 sound payouts against its own rules. An escalation waits for a trustee, so nothing is paid wrongly, but those payouts wait for a person. The prompt was not tuned to those cases (decision C-16).
- **No rate limits.** The API caps model calls per day (`DAILY_MODEL_CALL_CAP`) but not requests per caller.
- **The relayer can delay, not steal.** It pays gas for every transaction and holds no role. A compromised relayer can refuse to submit, which is denial of service; the fail-closed queue then holds the payouts.

## 7. Reproducing the evidence

```bash
bash scripts/test_all.sh                        # every suite, about 3 minutes
python scripts/run_demo.py --network anvil      # the 16 scenarios, self-checking
python scripts/verify.py --csv evidence/transactions.csv
```
