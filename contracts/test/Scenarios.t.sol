// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

import {AmanahLabels as L} from "../src/AmanahLabels.sol";
import {IAmanahVault} from "../src/IAmanahVault.sol";
import {AmanahBase} from "./utils/AmanahBase.sol";

/// @dev The 16 scripted scenarios of plan section 10, at contract level, with the plan's programme
/// numbers and a 10-minute cooling-off. Scenarios 1 to 4 are the base setup: the vault is deployed, two
/// trustees register the signers, set the mandates and add the beneficiaries.
contract ScenariosTest is AmanahBase {
    function test_scenario01to04_setup() public view {
        assertEq(uint8(vault.signers(address(this)).role), uint8(IAmanahVault.Role.NONE));
        assertEq(uint8(vault.signers(planner).role), uint8(IAmanahVault.Role.PLANNER));
        assertEq(vault.signers(auditor).lineage, L.LINEAGE_QWEN);
        assertEq(uint8(vault.signers(oracle).role), uint8(IAmanahVault.Role.POSTURE_ORACLE));
        assertEq(vault.mandates(ZKT).cap, 200 * USDC);
        assertEq(vault.mandates(REL).hardCeiling, 2000 * USDC);
        assertEq(vault.mandates(EDU).perBeneficiaryCap, 500 * USDC);
        assertTrue(vault.beneficiaries(ZKT, allowlisted[ZKT][0]).active);
    }

    function test_scenario05_donorDeposit() public {
        address donor = makeAddr("donor");
        usdc.mint(donor, 5000 * USDC);
        vm.prank(donor);
        assertTrue(usdc.transfer(address(vault), 5000 * USDC));
        assertEq(usdc.balanceOf(address(vault)), 105_000 * USDC);
    }

    /// 11 households at 150 USDC: 1,650 in all, under the 2,000 line, each under the 200 cap.
    function test_scenario06_routineBatchOfElevenHouseholds() public {
        _routineBatch();
        assertEq(vault.spentToday(ZKT), 1650 * USDC);
        assertEq(usdc.balanceOf(allowlisted[ZKT][10]), 150 * USDC);
    }

    /// The plan's 1,200 USDC grant is twice the flood relief per-beneficiary cap of 600 and reverts.
    /// With the cap at 1,500 (the proposal in docs/decisions.md) it is elevated and a trustee co-signs.
    function test_scenario07_aboveCapEmergencyGrant() public {
        IAmanahVault.Payout memory p = payout(REL, allowlisted[REL][0], 1200 * USDC);
        vm.expectRevert(IAmanahVault.BeneficiaryCapExceeded.selector);
        vault.tierOf(p);

        setMandate(REL, mandate(300, 2000, 3000, 1500));
        assertEq(vault.tierOf(p), 2);
        bytes[] memory machineOnly = routineSigs(p);
        vm.expectRevert(IAmanahVault.TrusteeRequired.selector);
        vault.execute(p, machineOnly);
        vault.execute(p, elevatedSigs(p));
        assertEq(usdc.balanceOf(p.beneficiary), 1200 * USDC);
    }

    function test_scenario08and09_refusalsAreAnchored() public {
        bytes32 induced = keccak256("induced transfer: chairman message");
        bytes32 injected = keccak256("prompt injection in an uploaded letter");
        vm.prank(auditor);
        bytes32 first = vault.anchorDecision(induced, IAmanahVault.Verdict.REJECT, keccak256("case file"));
        vm.prank(sentinel);
        bytes32 second = vault.anchorDecision(injected, IAmanahVault.Verdict.REJECT, keccak256("injection flag"));
        assertEq(uint8(vault.decisions(first).verdict), uint8(IAmanahVault.Verdict.REJECT));
        assertEq(vault.decisions(second).proposalId, injected);
        assertEq(usdc.balanceOf(address(vault)), 100_000 * USDC);
    }

    function test_scenario10_forcedAttackToAnUnlistedWalletReverts() public {
        IAmanahVault.Payout memory p = payout(REL, makeAddr("attacker wallet"), 2000 * USDC);
        bytes[] memory allThreeMachines = routineSigs(p);
        vm.expectRevert(IAmanahVault.NotAllowlisted.selector);
        vault.execute(p, allThreeMachines);
    }

    function test_scenario11_sameLineageQuorumReverts() public {
        registerSigner(claudeAuditor, IAmanahVault.Role.AUDITOR, L.LINEAGE_CLAUDE, L.VIEW_CASEFILE);
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory twoClaudes = sigsFor(p, keys(plannerKey, claudeAuditorKey, sentinelKey));
        vm.expectRevert(IAmanahVault.SameLineage.selector);
        vault.execute(p, twoClaudes);
    }

    function test_scenario12_plannerAddingABeneficiaryReverts() public {
        vm.prank(planner);
        vm.expectRevert(IAmanahVault.NotTrustee.selector);
        addBeneficiary(keys(plannerKey), ZKT, makeAddr("planner's wallet"));
    }

    /// After scenario 6's 1,650, the first 199 is routine, the second crosses the 2,000 line and needs a
    /// trustee, and once the trustee has co-signed it, the third passes the 400 beneficiary cap and reverts.
    function test_scenario13_structuringUnderTheCap() public {
        _routineBatch();
        address target = allowlisted[ZKT][11];

        IAmanahVault.Payout memory first = payout(ZKT, target, 199 * USDC);
        assertEq(vault.tierOf(first), 1);
        vault.execute(first, routineSigs(first));

        IAmanahVault.Payout memory second = payout(ZKT, target, 199 * USDC);
        assertEq(vault.tierOf(second), 2);
        bytes[] memory machineOnly = routineSigs(second);
        vm.expectRevert(IAmanahVault.TrusteeRequired.selector);
        vault.execute(second, machineOnly);
        vault.execute(second, elevatedSigs(second));

        IAmanahVault.Payout memory third = payout(ZKT, target, 199 * USDC);
        bytes[] memory withTrustee = elevatedSigs(third);
        vm.expectRevert(IAmanahVault.BeneficiaryCapExceeded.selector);
        vault.execute(third, withTrustee);
    }

    /// The limits in shared/fixture-data.md: a batch total outside (1,602, 1,801] breaks the story.
    function test_scenario13_needsScenarioSixBetween1602And1801() public {
        assertEq(_secondPaymentTier(1602), 1, "at 1,602 the second 199 does not cross the line");
        assertEq(_secondPaymentTier(1603), 2, "just above 1,602 it does");
        assertEq(_firstPaymentTier(1801), 1, "at 1,801 the first 199 is still routine");
        assertEq(_firstPaymentTier(1802), 2, "above 1,801 the first is already elevated");
    }

    function test_scenario14_raisedPostureElevatesTheNextRoutinePayout() public {
        vm.startPrank(oracle);
        vault.anchorReport(keccak256("red-team report"));
        vault.raisePosture(1, keccak256("red-team report"));
        vm.stopPrank();
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        assertEq(vault.tierOf(p), 2);
        bytes[] memory machineOnly = routineSigs(p);
        vm.expectRevert(IAmanahVault.TrusteeRequired.selector);
        vault.execute(p, machineOnly);
    }

    function test_scenario15_overrideOfAnAnchoredAuditorRejection() public {
        IAmanahVault.Payout memory p = payout(EDU, allowlisted[EDU][0], 450 * USDC);
        vm.prank(auditor);
        bytes32 refusal = vault.anchorDecision(p.proposalId, IAmanahVault.Verdict.REJECT, p.evidenceHash);
        vault.executeOverride(p, refusal, sigsFor(p, keys(plannerKey, trustee1Key, trustee2Key)));
        assertEq(usdc.balanceOf(p.beneficiary), 450 * USDC);
    }

    function test_scenario16_guardianPausesTwoTrusteesUnpause() public {
        vm.prank(guardian);
        vault.pause();
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        vm.expectRevert(Pausable.EnforcedPause.selector);
        vault.execute(p, sigs);
        unpause(twoTrustees());
        vault.execute(p, sigs);
    }

    function _routineBatch() internal {
        for (uint256 i = 0; i < 11; ++i) {
            payRoutine(ZKT, i, 150 * USDC);
        }
    }

    /// @dev Pays `batchUsdc` to other households, then returns the tier of a first 199 payout. Runs on a
    /// snapshot, so each measurement starts from the setup state.
    function _firstPaymentTier(uint256 batchUsdc) internal returns (uint8 tier) {
        uint256 snapshot = vm.snapshotState();
        _spend(batchUsdc);
        tier = vault.tierOf(payout(ZKT, allowlisted[ZKT][11], 199 * USDC));
        vm.revertToState(snapshot);
    }

    /// @dev As above, executes the first 199 payout, and returns the tier of the second.
    function _secondPaymentTier(uint256 batchUsdc) internal returns (uint8 tier) {
        uint256 snapshot = vm.snapshotState();
        _spend(batchUsdc);
        IAmanahVault.Payout memory first = payout(ZKT, allowlisted[ZKT][11], 199 * USDC);
        vault.execute(first, elevatedSigs(first));
        tier = vault.tierOf(payout(ZKT, allowlisted[ZKT][11], 199 * USDC));
        vm.revertToState(snapshot);
    }

    function _spend(uint256 batchUsdc) internal {
        for (uint256 i = 0; batchUsdc > 0; ++i) {
            uint256 amount = batchUsdc < 200 ? batchUsdc : 200;
            IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][i], amount * USDC);
            vault.execute(p, elevatedSigs(p));
            batchUsdc -= amount;
        }
    }
}
