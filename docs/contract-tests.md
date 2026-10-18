# Contract tests

Lane A's test record for `contracts/`. Recorded on 18 October 2026 with Foundry 1.7.1 and solc 0.8.26, OpenZeppelin Contracts v5.7.0 and forge-std v1.17.0.

## How to run

```bash
cd contracts
forge test                                  # everything: 109 tests
forge test --match-contract Invariant       # the 8 invariants only
forge test --no-match-contract Invariant    # unit, fuzz and vector tests only
```

A fresh clone needs the dependencies first: `git submodule update --init --recursive`, or `forge install`.

## What the suites hold

| Suite | File | Tests | What it covers |
|:--|:--|--:|:--|
| Unit and fuzz | `test/AmanahVault.t.sol` | 86 | Every custom error at least once, every happy path, the 14 cases named in plan task A3, boundary values for the cap, the 80% line, cooling-off and deadlines, and 4 fuzz tests at 256 runs each |
| EIP-712 vectors | `test/Vectors.t.sol` | 2 | `shared/vectors.json` matches the vault's digests and signatures |
| Demo scenarios | `test/Scenarios.t.sol` | 13 | Plan section 10's 16 scenarios with the plan's numbers, and the data limits in `shared/fixture-data.md` |
| Invariants | `test/Invariant.t.sol` | 8 | Random call sequences through `test/invariant/VaultHandler.sol` |

The cases named in plan task A3 carry an `A3:` comment in the test file.

## Invariants

Configuration in `contracts/foundry.toml`: `runs = 256`, `depth = 64`, so each invariant is checked after every one of 16,384 calls. The full suite takes about 28 seconds.

| Invariant | Property |
|:--|:--|
| `invariant_onlyAllowlisted` | USDC leaves the vault only to a wallet allowlisted for that programme and past cooling-off, and only through a payout the handler saw succeed |
| `invariant_dailyBudget` | No programme spends more than its daily budget in a day; nothing is paid outside an active mandate or above the hard ceiling |
| `invariant_machineBound` | Spend whose signer set held no trustee stays at or under 80% of each daily budget per day; machine signers alone never pay above the cap or under raised posture |
| `invariant_perBeneficiaryCap` | No beneficiary receives more than its programme's cap within a 30-day period |
| `invariant_lineageDistinct` | Every non-override payout had a planner and an auditor of different lineages |
| `invariant_postureMonotone` | Posture rose only through the posture oracle and fell only through `lowerPosture` with two trustees |
| `invariant_noReplay` | Every payout nonce and every governance nonce executed at most once |
| `invariant_authority` | Governance needed two distinct active trustees, overrides cited an unused auditor or sentinel refusal, single-key actions came from the right key, and nothing was paid while paused |

The last one goes beyond the seven the plan lists.

The handler mixes payouts, batches of payouts at the cap, overrides, exact replays, anchors, all six governance calls with valid and invalid signer sets and replayed nonces, pause, posture changes, cancellations and time warps of up to 3 days. It keeps its own record of the registry, allowlist, mandates and every amount paid. Each invariant compares against that record, not against the vault's own counters.

**The runs move real money.** Measured with `INVARIANT_STATS=true` over 256 runs of 64 calls:

| Per run | Minimum | Median | Maximum | Total |
|:--|--:|--:|--:|--:|
| Successful payouts | 0 | 14 | 31 | 3,604 |
| Successful overrides | 0 | 0 | 1 | 26 |
| Successful governance calls | 1 | 5 | 13 | 1,407 |
| USDC paid out | 0 | 3,101 | 7,460 | 776,173 |

The zakat programme's daily budget is 2,500 USDC and its 80% line is 2,000 USDC, so a median run reaches both.

## Do the tests catch bugs?

Twelve bugs were planted in `src/AmanahVault.sol`, one at a time. Every one made tests fail.

**Unit and fuzz suite.** Each of these made at least two tests fail:
- lineage check removed
- 80% line off by one
- allowlist check removed
- cooling-off off by one
- tier 2 trustee requirement skipped
- one trustee enough for governance
- payout nonce not marked as used
- posture allowed to stay level
- refusal reusable
- beneficiary cap off by one
- trustee floor off by one
- day rollover removed

**Invariant suite.** Each planted bug was caught by the invariant meant to catch it:

| Planted bug | Caught by |
|:--|:--|
| Allowlist check removed | `invariant_onlyAllowlisted` |
| Cooling-off check removed | `invariant_onlyAllowlisted` |
| Daily budget check removed | `invariant_dailyBudget` |
| 80% line removed | `invariant_machineBound` |
| Beneficiary cap removed | `invariant_perBeneficiaryCap` |
| Lineage check removed | `invariant_lineageDistinct` |
| Tier 2 trustee requirement removed | `invariant_machineBound` |
| One trustee enough for governance | `invariant_authority`, `invariant_postureMonotone` |
| Posture ratchet removed | `invariant_postureMonotone` |
| Payout nonce not marked as used | `invariant_noReplay` |
| Override accepted without a refusal | `invariant_authority` |
| Pause ignored by `execute` | `invariant_authority` |

## On Anvil

`bash contracts/script/anvil_smoke.sh` runs against a running Anvil with the fixture deployed. It signs typed data with `cast wallet sign` and sends real transactions:
- scenario 6, a routine payout, succeeds;
- scenarios 10, 11 and 12 are mined and reverted with `NotAllowlisted`, `SameLineage` and `NotTrustee`;
- scenario 16's pause blocks a payout with `EnforcedPause`, and the same payout succeeds after two trustees unpause.

All 8 checks passed on 18 October 2026, and again on a second run against the same node.

## EIP-712 cross-check

`shared/vectors.json` holds the domain separator, the type hashes, and one payout with its digest and signature. It also holds one call for each of the six governance actions, with its `paramsHash`, digest and signature. The vault sits at a fixed address on chain 84532, and the signing keys are `keccak256` of the labels in the file, so the file holds no secret. Python's eth-account 0.13 reproduces every digest, every `paramsHash` and every signature byte for byte. Regenerate the file with `WRITE_VECTORS=true forge test --match-test test_writeVectors`.
