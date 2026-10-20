# Static analysis and coverage

Run on 20 October 2026 over the contracts that hold money (decision E-33). The security self-assessment summarises this page; the raw Slither output is `evidence/static-analysis/slither.json`.

## Slither

[Slither](https://github.com/crytic/slither) 0.11.6, Trail of Bits' static analyser, with all 102 detectors, over `contracts/src/` (libraries, tests and scripts excluded):

```text
hafiz@amanah-wallet:~/contracts$ uvx --from "slither-analyzer==0.11.6" slither . --filter-paths "lib/|test/|script/" --exclude-dependencies
. analyzed (30 contracts with 102 detectors), 11 result(s) found
```

No finding is high. Each of the 11 is triaged below, and none needs a change before a pilot.

| impact | detector | where | verdict |
|:--|:--|:--|:--|
| medium | incorrect-equality | `_spentIn`: `s.window == window` | **False positive.** The detector flags strict equality on values derived from time. Here `window` is the index of the current day (or 30-day period) and `s.window` is the index of the bucket last written; equality is exactly the rule "spend counts only within its own window". Nobody can make the comparison fail in their favour: a mismatch zeroes the bucket only when time has really moved into a new window, which is when it should. The daily budget and per-beneficiary invariants hold over 16,384 fuzzed calls each. |
| low | timestamp, 6 places | mandate expiry (`tierOf`), cooling-off (`cancelBeneficiary`, `_checkPayout`), payout and governance deadlines (`_checkPayout`, `_requireTwoTrustees`), day and period windows (`_addSpend`, `_spentIn`) | **Accepted by design.** Each comparison is meant to use time. A block producer can shift a timestamp by seconds (on Base, the sequencer, within the protocol's bounds). The worst effect is that a deadline or a cooling-off ends seconds early or late, or a payout near midnight counts against the next day's budget, which day windows allow anyway. No shift lets more than a window's budget move within one window, or a beneficiary past its cap. |
| informational | costly-loop | the constructor's loop over the three trustees | **Accepted.** A fixed loop of three, run once at deployment. |
| informational | unindexed-event-address, 3 events | `ReportAnchored`, `SignerRegistered`, `SignerActiveSet` | **Accepted for now.** Indexing the address would let an explorer filter these events by key. The backend reads them by scanning the vault's own logs, so nothing depends on it; it waits for the next version of the contract rather than a redeployment now. |

## Coverage

`forge coverage --report summary --ir-minimum`, all 115 tests (measured again on 20 October after three invariants were added; the vault's row did not change):

| file | lines | statements | branches | functions |
|:--|--:|--:|--:|--:|
| `src/AmanahVault.sol` | 97.9% (186 of 190) | 98.4% (246 of 250) | **100% (53 of 53)** | **100% (33 of 33)** |
| `src/TestUSDC.sol` | 100% (4 of 4) | 100% (2 of 2) | none | 100% (2 of 2) |

Every branch and every function of the vault is exercised. The four lines that report no hits are each a call to an internal function inside a tested function: `_requirePostureOracle()` in `anchorReport` and in `raisePosture`, `_unpause()` in `unpause`, and `_pause()` in `pause`. In each case the next line is counted as covered, and named tests call the function (`test_anchorReport_byOracle`, `test_raisePosture_onlyUpwards`, `test_pause_blocksPayoutsUntilTwoTrusteesUnpause`), so the zero is the line map of an instrumented build, not an untested path. The deployment scripts and test helpers are not counted: scripts are exercised by the Anvil demo and the FISCO run, not by unit tests.
