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
