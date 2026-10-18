// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

import {AmanahLabels as L} from "../src/AmanahLabels.sol";
import {AmanahVault} from "../src/AmanahVault.sol";
import {IAmanahVault} from "../src/IAmanahVault.sol";
import {AmanahBase} from "./utils/AmanahBase.sol";

/// @dev Unit and fuzz tests for AmanahVault. The cases named in plan task A3 are marked "A3:".
contract AmanahVaultTest is AmanahBase {
    // Construction and EIP-712

    function test_constructor_registersTrusteesAndGuardian() public view {
        IAmanahVault.Signer memory t = vault.signers(trustee1);
        assertEq(uint8(t.role), uint8(IAmanahVault.Role.TRUSTEE));
        assertEq(t.lineage, L.LINEAGE_HUMAN);
        assertEq(t.evidenceView, L.VIEW_HUMAN);
        assertTrue(t.active);
        assertEq(uint8(vault.signers(trustee3).role), uint8(IAmanahVault.Role.TRUSTEE));
        assertEq(uint8(vault.signers(guardian).role), uint8(IAmanahVault.Role.GUARDIAN));
        assertEq(vault.activeTrustees(), 3);
        assertEq(address(vault.usdc()), address(usdc));
        assertEq(vault.coolingOff(), COOLING_OFF);
    }

    function test_constructor_deployerHoldsNoRole() public view {
        assertEq(uint8(vault.signers(address(this)).role), uint8(IAmanahVault.Role.NONE));
    }

    function test_constructor_revertsOnZeroAddress() public {
        vm.expectRevert(AmanahVault.ZeroAddress.selector);
        new AmanahVault(address(0), [trustee1, trustee2, trustee3], guardian, COOLING_OFF);
        vm.expectRevert(AmanahVault.ZeroAddress.selector);
        new AmanahVault(address(usdc), [trustee1, address(0), trustee3], guardian, COOLING_OFF);
        vm.expectRevert(AmanahVault.ZeroAddress.selector);
        new AmanahVault(address(usdc), [trustee1, trustee2, trustee3], address(0), COOLING_OFF);
    }

    function test_constructor_revertsOnRepeatedKey() public {
        vm.expectRevert(IAmanahVault.DuplicateSigner.selector);
        new AmanahVault(address(usdc), [trustee1, trustee1, trustee3], guardian, COOLING_OFF);
        vm.expectRevert(IAmanahVault.DuplicateSigner.selector);
        new AmanahVault(address(usdc), [trustee1, trustee2, trustee3], trustee3, COOLING_OFF);
    }

    function test_eip712Domain_matchesPlan() public view {
        (, string memory name, string memory version, uint256 chainId, address verifyingContract,,) =
            vault.eip712Domain();
        assertEq(name, "AmanahVault");
        assertEq(version, "1");
        assertEq(chainId, block.chainid);
        assertEq(verifyingContract, address(vault));
    }

    function test_hashes_matchIndependentImplementation() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        assertEq(vault.PAYOUT_TYPEHASH(), PAYOUT_TYPEHASH);
        assertEq(vault.GOVERNANCE_TYPEHASH(), GOVERNANCE_TYPEHASH);
        assertEq(vault.hashPayout(p), payoutDigest(p));
        assertEq(
            vault.hashGovernance(ACTION_UNPAUSE, bytes32(uint256(7)), 9, 1234),
            govDigest(ACTION_UNPAUSE, bytes32(uint256(7)), 9, 1234)
        );
        assertEq(vault.ACTION_LOWER_POSTURE(), ACTION_LOWER_POSTURE);
        assertEq(vault.ACTION_REGISTER_SIGNER(), ACTION_REGISTER_SIGNER);
        assertEq(vault.ACTION_SET_SIGNER_ACTIVE(), ACTION_SET_SIGNER_ACTIVE);
        assertEq(vault.ACTION_SET_MANDATE(), ACTION_SET_MANDATE);
        assertEq(vault.ACTION_ADD_BENEFICIARY(), ACTION_ADD_BENEFICIARY);
        assertEq(vault.ACTION_UNPAUSE(), ACTION_UNPAUSE);
    }

    function test_signatures_areBoundToTheChain() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        vm.chainId(84532);
        vm.expectRevert(IAmanahVault.UnknownSigner.selector);
        vault.execute(p, sigs);
    }

    // Routine and elevated payouts

    /// A3: routine payout with planner, auditor and sentinel.
    function test_execute_routinePayout() public {
        address to = allowlisted[ZKT][0];
        IAmanahVault.Payout memory p = payout(ZKT, to, 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        assertEq(vault.tierOf(p), 1);

        vm.expectEmit(address(vault));
        emit IAmanahVault.PayoutExecuted(p.proposalId, ZKT, to, 150 * USDC, 1, addrs(planner, auditor, sentinel), false);
        vm.prank(attacker); // anyone may relay; the signatures carry the authority
        vault.execute(p, sigs);

        assertEq(usdc.balanceOf(to), 150 * USDC);
        assertEq(usdc.balanceOf(address(vault)), 100_000 * USDC - 150 * USDC);
        assertEq(vault.spentToday(ZKT), 150 * USDC);
        assertEq(vault.spentThisPeriod(ZKT, to), 150 * USDC);
        assertTrue(vault.nonceUsed(p.nonce));
    }

    function test_execute_acceptsSignaturesInAnyOrder() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        vault.execute(p, sigsFor(p, keys(sentinelKey, plannerKey, auditorKey)));
        assertEq(usdc.balanceOf(p.beneficiary), 150 * USDC);
    }

    /// A3: elevated above the cap with a trustee.
    function test_execute_aboveCapNeedsTrustee() public {
        IAmanahVault.Payout memory p = payout(REL, allowlisted[REL][0], 450 * USDC);
        assertEq(vault.tierOf(p), 2);
        bytes[] memory machineOnly = routineSigs(p);
        vm.expectRevert(IAmanahVault.TrusteeRequired.selector);
        vault.execute(p, machineOnly);

        vm.expectEmit(address(vault));
        emit IAmanahVault.PayoutExecuted(
            p.proposalId, REL, p.beneficiary, 450 * USDC, 2, addrs(planner, auditor, sentinel, trustee1), false
        );
        vault.execute(p, elevatedSigs(p));
        assertEq(usdc.balanceOf(p.beneficiary), 450 * USDC);
    }

    function test_execute_trusteeMayCosignARoutinePayout() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        vault.execute(p, elevatedSigs(p));
        assertEq(usdc.balanceOf(p.beneficiary), 150 * USDC);
    }

    function test_tierOf_capBoundary() public {
        assertEq(vault.tierOf(payout(ZKT, allowlisted[ZKT][0], 200 * USDC)), 1);
        assertEq(vault.tierOf(payout(ZKT, allowlisted[ZKT][0], 200 * USDC + 1)), 2);
    }

    /// A3: the 80% line flips tier 1 to tier 2.
    function test_eightyPercentLine_flipsTier() public {
        // ZKT: daily budget 2,500, so the line is at 2,000. Ten routine payouts of 200 reach it exactly.
        for (uint256 i = 0; i < 10; ++i) {
            payRoutine(ZKT, i, 200 * USDC);
        }
        assertEq(vault.spentToday(ZKT), 2000 * USDC);

        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][10], 1);
        assertEq(vault.tierOf(p), 2);
        bytes[] memory machineOnly = routineSigs(p);
        vm.expectRevert(IAmanahVault.TrusteeRequired.selector);
        vault.execute(p, machineOnly);
        vault.execute(p, elevatedSigs(p));
    }

    /// A3: posture raised flips every payout to tier 2.
    function test_raisedPosture_makesEveryPayoutElevated() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 1 * USDC);
        IAmanahVault.Payout memory q = payout(EDU, allowlisted[EDU][0], 1 * USDC);
        assertEq(vault.tierOf(p), 1);
        assertEq(vault.tierOf(q), 1);

        vm.prank(oracle);
        vault.raisePosture(1, keccak256("report"));
        assertEq(vault.tierOf(p), 2);
        assertEq(vault.tierOf(q), 2);

        bytes[] memory machineOnly = routineSigs(p);
        vm.expectRevert(IAmanahVault.TrusteeRequired.selector);
        vault.execute(p, machineOnly);
        vault.execute(p, elevatedSigs(p));
    }

    // Quorum checks

    /// A3: same lineage reverts with SameLineage.
    function test_execute_sameLineageReverts() public {
        registerSigner(claudeAuditor, IAmanahVault.Role.AUDITOR, L.LINEAGE_CLAUDE, L.VIEW_CASEFILE);
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = sigsFor(p, keys(plannerKey, claudeAuditorKey, sentinelKey));
        vm.expectRevert(IAmanahVault.SameLineage.selector);
        vault.execute(p, sigs);
    }

    function test_execute_sameLineageRevertsEvenWithTrustees() public {
        registerSigner(claudeAuditor, IAmanahVault.Role.AUDITOR, L.LINEAGE_CLAUDE, L.VIEW_CASEFILE);
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = sigsFor(p, keys(plannerKey, claudeAuditorKey, sentinelKey, trustee1Key, trustee2Key));
        vm.expectRevert(IAmanahVault.SameLineage.selector);
        vault.execute(p, sigs);
    }

    function test_execute_missingSentinelReverts() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = sigsFor(p, keys(plannerKey, auditorKey, trustee1Key));
        vm.expectRevert(IAmanahVault.QuorumIncomplete.selector);
        vault.execute(p, sigs);
    }

    function test_execute_twoPlannersRevert() public {
        (address planner2, uint256 planner2Key) = makeAddrAndKey("planner2");
        registerSigner(planner2, IAmanahVault.Role.PLANNER, L.LINEAGE_GPT, L.VIEW_CONVERSATION);
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = sigsFor(p, keys(plannerKey, planner2Key, auditorKey, sentinelKey));
        vm.expectRevert(IAmanahVault.QuorumIncomplete.selector);
        vault.execute(p, sigs);
    }

    function test_execute_guardianSignatureReverts() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = sigsFor(p, keys(plannerKey, auditorKey, sentinelKey, guardianKey));
        vm.expectRevert(IAmanahVault.QuorumIncomplete.selector);
        vault.execute(p, sigs);
    }

    function test_execute_unknownSignerReverts() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = sigsFor(p, keys(plannerKey, attackerKey, sentinelKey));
        vm.expectRevert(IAmanahVault.UnknownSigner.selector);
        vault.execute(p, sigs);
    }

    function test_execute_inactiveSignerReverts() public {
        setSignerActive(sentinel, false);
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        vm.expectRevert(IAmanahVault.InactiveSigner.selector);
        vault.execute(p, sigs);

        setSignerActive(sentinel, true);
        vault.execute(p, sigs);
    }

    function test_execute_duplicateSignerReverts() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = sigsFor(p, keys(plannerKey, auditorKey, sentinelKey, auditorKey));
        vm.expectRevert(IAmanahVault.DuplicateSigner.selector);
        vault.execute(p, sigs);
    }

    function test_execute_malformedSignatureReverts() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        sigs[1] = abi.encodePacked(bytes32(uint256(1)), bytes32(uint256(2)));
        vm.expectRevert(abi.encodeWithSelector(ECDSA.ECDSAInvalidSignatureLength.selector, 64));
        vault.execute(p, sigs);
    }

    function test_execute_signatureOverOtherAmountReverts() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        p.amount = 199 * USDC;
        vm.expectRevert(IAmanahVault.UnknownSigner.selector);
        vault.execute(p, sigs);
    }

    // Payout limits

    /// A3: a wallet that is not allowlisted reverts with NotAllowlisted.
    function test_execute_notAllowlistedReverts() public {
        IAmanahVault.Payout memory p = payout(ZKT, attacker, 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        vm.expectRevert(IAmanahVault.NotAllowlisted.selector);
        vault.execute(p, sigs);
    }

    function test_execute_allowlistIsPerProgramme() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[REL][0], 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        vm.expectRevert(IAmanahVault.NotAllowlisted.selector);
        vault.execute(p, sigs);
    }

    /// A3: cooling-off reverts with CoolingOff, then succeeds after vm.warp.
    function test_execute_coolingOffThenSucceedsAfterWarp() public {
        address newcomer = makeAddr("newcomer");
        addBeneficiary(ZKT, newcomer);
        IAmanahVault.Payout memory p = payout(ZKT, newcomer, 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        vm.expectRevert(IAmanahVault.CoolingOff.selector);
        vault.execute(p, sigs);

        vm.warp(block.timestamp + COOLING_OFF - 1);
        vm.expectRevert(IAmanahVault.CoolingOff.selector);
        vault.execute(p, sigs);

        vm.warp(block.timestamp + 1);
        vault.execute(p, sigs);
        assertEq(usdc.balanceOf(newcomer), 150 * USDC);
    }

    function test_execute_expiredReverts() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        vm.warp(p.deadline + 1);
        vm.expectRevert(IAmanahVault.Expired.selector);
        vault.execute(p, sigs);
    }

    function test_execute_atDeadlineSucceeds() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        vm.warp(p.deadline);
        vault.execute(p, sigs);
    }

    function test_execute_replayReverts() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        vault.execute(p, sigs);
        vm.expectRevert(IAmanahVault.NonceUsed.selector);
        vault.execute(p, sigs);
    }

    function test_execute_aboveHardCeilingReverts() public {
        IAmanahVault.Payout memory p = payout(REL, allowlisted[REL][0], 2000 * USDC + 1);
        bytes[] memory sigs = elevatedSigs(p);
        vm.expectRevert(IAmanahVault.AboveHardCeiling.selector);
        vault.execute(p, sigs);
    }

    function test_execute_dailyBudgetExceededReverts() public {
        // EDU: daily budget 2,000 and a per-beneficiary cap of 500. Four elevated payouts of 500 use it up.
        for (uint256 i = 0; i < 4; ++i) {
            IAmanahVault.Payout memory paid = payout(EDU, allowlisted[EDU][i], 500 * USDC);
            vault.execute(paid, elevatedSigs(paid));
        }
        IAmanahVault.Payout memory p = payout(EDU, allowlisted[EDU][4], 1);
        bytes[] memory sigs = elevatedSigs(p);
        vm.expectRevert(IAmanahVault.DailyBudgetExceeded.selector);
        vault.execute(p, sigs);
    }

    /// A3: structuring. Ten payouts of 199 to one beneficiary under a cap of 200 hit BeneficiaryCapExceeded.
    function test_structuring_tenPaymentsOf199HitBeneficiaryCap() public {
        address to = allowlisted[ZKT][0];
        uint256 reverted;
        for (uint256 i = 0; i < 10; ++i) {
            IAmanahVault.Payout memory p = payout(ZKT, to, 199 * USDC);
            assertEq(p.amount < 200 * USDC, true);
            bytes[] memory sigs = routineSigs(p);
            if (vault.spentThisPeriod(ZKT, to) + p.amount > 400 * USDC) {
                vm.expectRevert(IAmanahVault.BeneficiaryCapExceeded.selector);
                ++reverted;
            }
            vault.execute(p, sigs);
        }
        assertEq(usdc.balanceOf(to), 398 * USDC);
        assertEq(reverted, 8);
    }

    function test_mandate_inactiveReverts() public {
        IAmanahVault.Mandate memory m = mandate(200, 1500, 2500, 400);
        m.active = false;
        setMandate(ZKT, m);
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        vm.expectRevert(IAmanahVault.MandateInactive.selector);
        vault.tierOf(p);
    }

    function test_mandate_expiredReverts() public {
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        vm.warp(START + 365 days + 1);
        p.deadline = block.timestamp + 1 hours;
        bytes[] memory sigs = routineSigs(p);
        vm.expectRevert(IAmanahVault.MandateInactive.selector);
        vault.execute(p, sigs);
    }

    function test_mandate_unknownProgrammeReverts() public {
        IAmanahVault.Payout memory p = payout(keccak256("NO-SUCH-PROGRAMME"), allowlisted[ZKT][0], 1);
        vm.expectRevert(IAmanahVault.MandateInactive.selector);
        vault.tierOf(p);
    }

    /// A3: day rollover resets spentToday.
    function test_dayRollover_resetsSpentToday() public {
        for (uint256 i = 0; i < 10; ++i) {
            payRoutine(ZKT, i, 200 * USDC);
        }
        assertEq(vault.spentToday(ZKT), 2000 * USDC);
        assertEq(vault.tierOf(payout(ZKT, allowlisted[ZKT][10], 1)), 2);

        vm.warp((block.timestamp / 1 days + 1) * 1 days);
        assertEq(vault.spentToday(ZKT), 0);
        assertEq(vault.tierOf(payout(ZKT, allowlisted[ZKT][10], 1)), 1);
        payRoutine(ZKT, 10, 200 * USDC);
        assertEq(vault.spentToday(ZKT), 200 * USDC);
    }

    function test_periodRollover_resetsBeneficiaryCap() public {
        address to = allowlisted[ZKT][0];
        payRoutine(ZKT, 0, 200 * USDC);
        payRoutine(ZKT, 0, 200 * USDC);
        IAmanahVault.Payout memory p = payout(ZKT, to, 1);
        vm.expectRevert(IAmanahVault.BeneficiaryCapExceeded.selector);
        vault.tierOf(p);

        vm.warp((block.timestamp / 30 days + 1) * 30 days);
        assertEq(vault.spentThisPeriod(ZKT, to), 0);
        payRoutine(ZKT, 0, 200 * USDC);
        assertEq(vault.spentThisPeriod(ZKT, to), 200 * USDC);
    }

    // Overrides

    /// A3: an override without an anchored refusal reverts with NoSuchRefusal.
    function test_override_withoutAnchoredRefusalReverts() public {
        IAmanahVault.Payout memory p = payout(EDU, allowlisted[EDU][0], 400 * USDC);
        bytes[] memory sigs = sigsFor(p, keys(plannerKey, trustee1Key, trustee2Key));
        vm.expectRevert(IAmanahVault.NoSuchRefusal.selector);
        vault.executeOverride(p, keccak256("no such anchor"), sigs);
    }

    function test_override_afterAuditorRejectionPays() public {
        IAmanahVault.Payout memory p = payout(EDU, allowlisted[EDU][0], 400 * USDC);
        vm.prank(auditor);
        bytes32 anchorId = vault.anchorDecision(p.proposalId, IAmanahVault.Verdict.REJECT, p.evidenceHash);
        bytes[] memory sigs = sigsFor(p, keys(plannerKey, trustee1Key, trustee2Key));

        vm.expectEmit(address(vault));
        emit IAmanahVault.PayoutExecuted(
            p.proposalId, EDU, p.beneficiary, 400 * USDC, 3, addrs(planner, trustee1, trustee2), true
        );
        vault.executeOverride(p, anchorId, sigs);
        assertEq(usdc.balanceOf(p.beneficiary), 400 * USDC);
        assertTrue(vault.refusalUsed(anchorId));
        assertEq(vault.spentToday(EDU), 400 * USDC);
    }

    function test_override_afterSentinelRejectionAndAuditorEscalationPays() public {
        IAmanahVault.Payout memory p = payout(EDU, allowlisted[EDU][0], 100 * USDC);
        vm.prank(sentinel);
        bytes32 sentinelAnchor = vault.anchorDecision(p.proposalId, IAmanahVault.Verdict.REJECT, p.evidenceHash);
        vault.executeOverride(p, sentinelAnchor, sigsFor(p, keys(plannerKey, trustee1Key, trustee3Key)));

        IAmanahVault.Payout memory q = payout(EDU, allowlisted[EDU][1], 100 * USDC);
        vm.prank(auditor);
        bytes32 auditorAnchor = vault.anchorDecision(q.proposalId, IAmanahVault.Verdict.ESCALATE, q.evidenceHash);
        vault.executeOverride(q, auditorAnchor, sigsFor(q, keys(plannerKey, trustee2Key, trustee3Key, sentinelKey)));
        assertEq(usdc.balanceOf(q.beneficiary), 100 * USDC);
    }

    function test_override_mayExceedTheCapButNotTheHardCeiling() public {
        // REL: cap 300, per-beneficiary cap 600, hard ceiling 2,000.
        IAmanahVault.Payout memory p = payout(REL, allowlisted[REL][0], 550 * USDC);
        bytes32 anchorId = anchorRefusal(auditor, p);
        vault.executeOverride(p, anchorId, sigsFor(p, keys(plannerKey, trustee1Key, trustee2Key)));
        assertEq(usdc.balanceOf(p.beneficiary), 550 * USDC);

        setMandate(REL, mandate(300, 2000, 3000, 5000));
        IAmanahVault.Payout memory q = payout(REL, allowlisted[REL][1], 2000 * USDC + 1);
        bytes32 secondAnchor = anchorRefusal(auditor, q);
        bytes[] memory sigs = sigsFor(q, keys(plannerKey, trustee1Key, trustee2Key));
        vm.expectRevert(IAmanahVault.AboveHardCeiling.selector);
        vault.executeOverride(q, secondAnchor, sigs);
    }

    function test_override_respectsTheBeneficiaryCap() public {
        IAmanahVault.Payout memory p = payout(EDU, allowlisted[EDU][0], 500 * USDC + 1);
        bytes32 anchorId = anchorRefusal(auditor, p);
        bytes[] memory sigs = sigsFor(p, keys(plannerKey, trustee1Key, trustee2Key));
        vm.expectRevert(IAmanahVault.BeneficiaryCapExceeded.selector);
        vault.executeOverride(p, anchorId, sigs);
    }

    function test_override_refusalCanBeCitedOnce() public {
        IAmanahVault.Payout memory p = payout(EDU, allowlisted[EDU][0], 100 * USDC);
        bytes32 anchorId = anchorRefusal(auditor, p);
        vault.executeOverride(p, anchorId, sigsFor(p, keys(plannerKey, trustee1Key, trustee2Key)));

        IAmanahVault.Payout memory again = payout(EDU, allowlisted[EDU][0], 100 * USDC);
        again.proposalId = p.proposalId;
        bytes[] memory sigs = sigsFor(again, keys(plannerKey, trustee1Key, trustee2Key));
        vm.expectRevert(IAmanahVault.NoSuchRefusal.selector);
        vault.executeOverride(again, anchorId, sigs);
    }

    function test_override_rejectsApprovalsPlannerRefusalsAndOtherProposals() public {
        IAmanahVault.Payout memory p = payout(EDU, allowlisted[EDU][0], 100 * USDC);
        bytes[] memory sigs = sigsFor(p, keys(plannerKey, trustee1Key, trustee2Key));

        vm.prank(auditor);
        bytes32 approval = vault.anchorDecision(p.proposalId, IAmanahVault.Verdict.APPROVE, p.evidenceHash);
        vm.expectRevert(IAmanahVault.NoSuchRefusal.selector);
        vault.executeOverride(p, approval, sigs);

        vm.prank(planner);
        bytes32 plannerRefusal = vault.anchorDecision(p.proposalId, IAmanahVault.Verdict.REJECT, p.evidenceHash);
        vm.expectRevert(IAmanahVault.NoSuchRefusal.selector);
        vault.executeOverride(p, plannerRefusal, sigs);

        vm.prank(auditor);
        bytes32 otherProposal = vault.anchorDecision(keccak256("other"), IAmanahVault.Verdict.REJECT, p.evidenceHash);
        vm.expectRevert(IAmanahVault.NoSuchRefusal.selector);
        vault.executeOverride(p, otherProposal, sigs);
    }

    function test_override_needsTwoTrusteesAndThePlanner() public {
        IAmanahVault.Payout memory p = payout(EDU, allowlisted[EDU][0], 100 * USDC);
        bytes32 anchorId = anchorRefusal(auditor, p);

        bytes[] memory oneTrustee = sigsFor(p, keys(plannerKey, trustee1Key, sentinelKey));
        vm.expectRevert(IAmanahVault.TrusteeRequired.selector);
        vault.executeOverride(p, anchorId, oneTrustee);

        bytes[] memory noPlanner = sigsFor(p, keys(trustee1Key, trustee2Key, trustee3Key));
        vm.expectRevert(IAmanahVault.QuorumIncomplete.selector);
        vault.executeOverride(p, anchorId, noPlanner);

        bytes[] memory guardianIncluded = sigsFor(p, keys(plannerKey, trustee1Key, trustee2Key, guardianKey));
        vm.expectRevert(IAmanahVault.QuorumIncomplete.selector);
        vault.executeOverride(p, anchorId, guardianIncluded);
    }

    function test_override_stillNeedsTheAllowlist() public {
        IAmanahVault.Payout memory p = payout(EDU, attacker, 100 * USDC);
        bytes32 anchorId = anchorRefusal(auditor, p);
        bytes[] memory sigs = sigsFor(p, keys(plannerKey, trustee1Key, trustee2Key));
        vm.expectRevert(IAmanahVault.NotAllowlisted.selector);
        vault.executeOverride(p, anchorId, sigs);
    }

    // Anchoring and posture

    function test_anchorDecision_storesAndEmits() public {
        bytes32 proposalId = keccak256("proposal");
        bytes32 evidenceHash = keccak256("evidence");
        bytes32 expectedId =
            keccak256(abi.encode(proposalId, IAmanahVault.Verdict.REJECT, evidenceHash, auditor, block.number));
        vm.expectEmit(address(vault));
        emit IAmanahVault.DecisionAnchored(
            expectedId, proposalId, uint8(IAmanahVault.Verdict.REJECT), auditor, evidenceHash
        );
        vm.prank(auditor);
        bytes32 anchorId = vault.anchorDecision(proposalId, IAmanahVault.Verdict.REJECT, evidenceHash);
        assertEq(anchorId, expectedId);

        IAmanahVault.Decision memory d = vault.decisions(anchorId);
        assertEq(d.proposalId, proposalId);
        assertEq(uint8(d.verdict), uint8(IAmanahVault.Verdict.REJECT));
        assertEq(d.signer, auditor);
        assertEq(d.blockNumber, block.number);
    }

    function test_anchorDecision_onlyActiveCheckers() public {
        vm.prank(trustee1);
        vm.expectRevert(AmanahVault.NotChecker.selector);
        vault.anchorDecision(keccak256("p"), IAmanahVault.Verdict.REJECT, bytes32(0));

        vm.prank(attacker);
        vm.expectRevert(AmanahVault.NotChecker.selector);
        vault.anchorDecision(keccak256("p"), IAmanahVault.Verdict.REJECT, bytes32(0));

        setSignerActive(auditor, false);
        vm.prank(auditor);
        vm.expectRevert(AmanahVault.NotChecker.selector);
        vault.anchorDecision(keccak256("p"), IAmanahVault.Verdict.REJECT, bytes32(0));
    }

    function test_anchorDecision_rejectsVerdictNone() public {
        vm.prank(sentinel);
        vm.expectRevert(AmanahVault.InvalidVerdict.selector);
        vault.anchorDecision(keccak256("p"), IAmanahVault.Verdict.NONE, bytes32(0));
    }

    function test_anchorReport_byOracle() public {
        vm.expectEmit(address(vault));
        emit IAmanahVault.ReportAnchored(keccak256("report"), oracle);
        vm.prank(oracle);
        vault.anchorReport(keccak256("report"));
        assertEq(vault.lastReportHash(), keccak256("report"));
        assertEq(vault.posture(), 0);
    }

    function test_anchorReport_andRaisePosture_onlyOracle() public {
        vm.prank(planner);
        vm.expectRevert(IAmanahVault.NotPostureOracle.selector);
        vault.anchorReport(keccak256("report"));

        vm.prank(trustee1);
        vm.expectRevert(IAmanahVault.NotPostureOracle.selector);
        vault.raisePosture(1, keccak256("report"));

        setSignerActive(oracle, false);
        vm.prank(oracle);
        vm.expectRevert(IAmanahVault.NotPostureOracle.selector);
        vault.raisePosture(1, keccak256("report"));
    }

    function test_raisePosture_onlyUpwards() public {
        vm.expectEmit(address(vault));
        emit IAmanahVault.PostureRaised(1, keccak256("report"));
        vm.prank(oracle);
        vault.raisePosture(1, keccak256("report"));
        assertEq(vault.posture(), 1);
        assertEq(vault.postureChangedAt(), block.timestamp);
        assertEq(vault.lastReportHash(), keccak256("report"));

        vm.prank(oracle);
        vm.expectRevert(IAmanahVault.PostureCanOnlyRise.selector);
        vault.raisePosture(1, keccak256("again"));

        vm.prank(oracle);
        vault.raisePosture(2, keccak256("worse"));
        assertEq(vault.posture(), 2);
    }

    /// A3: lowerPosture by one trustee reverts, by two succeeds.
    function test_lowerPosture_needsTwoTrustees() public {
        vm.prank(oracle);
        vault.raisePosture(2, keccak256("report"));

        vm.expectRevert(IAmanahVault.QuorumIncomplete.selector);
        lowerPosture(0, keys(trustee1Key));

        vm.expectEmit(address(vault));
        emit IAmanahVault.PostureLowered(0);
        lowerPosture(0, keys(trustee1Key, trustee3Key));
        assertEq(vault.posture(), 0);
    }

    function test_lowerPosture_onlyDownwards() public {
        vm.prank(oracle);
        vault.raisePosture(1, keccak256("report"));
        vm.expectRevert(IAmanahVault.PostureCanOnlyFall.selector);
        lowerPosture(1, twoTrustees());
        vm.expectRevert(IAmanahVault.PostureCanOnlyFall.selector);
        lowerPosture(2, twoTrustees());
    }

    function test_lowerPosture_oracleCannotSign() public {
        vm.prank(oracle);
        vault.raisePosture(1, keccak256("report"));
        vm.expectRevert(IAmanahVault.NotTrustee.selector);
        lowerPosture(0, keys(oracleKey, trustee1Key));
    }

    // Governance mechanics

    /// A3: a governance nonce replay reverts with GovNonceUsed.
    function test_governance_nonceReplayReverts() public {
        address wallet = makeAddr("replayed");
        bytes32 idHash = keccak256("id");
        (uint256 n, uint256 d) = nextGov();
        bytes[] memory sigs =
            govSigs(ACTION_ADD_BENEFICIARY, keccak256(abi.encode(ZKT, wallet, idHash)), n, d, twoTrustees());
        vault.addBeneficiary(ZKT, wallet, idHash, n, d, sigs);
        assertTrue(vault.govNonceUsed(n));
        vm.expectRevert(IAmanahVault.GovNonceUsed.selector);
        vault.addBeneficiary(ZKT, wallet, idHash, n, d, sigs);
    }

    function test_governance_expiredReverts() public {
        (uint256 n, uint256 d) = nextGov();
        bytes[] memory sigs = govSigs(ACTION_UNPAUSE, keccak256(abi.encode()), n, d, twoTrustees());
        vm.warp(d + 1);
        vm.expectRevert(IAmanahVault.Expired.selector);
        vault.unpause(n, d, sigs);
    }

    function test_governance_repeatedTrusteeReverts() public {
        vm.expectRevert(IAmanahVault.DuplicateSigner.selector);
        lowerPosture(0, keys(trustee1Key, trustee1Key));
    }

    function test_governance_noSignaturesReverts() public {
        vm.expectRevert(IAmanahVault.QuorumIncomplete.selector);
        lowerPosture(0, new uint256[](0));
    }

    function test_governance_threeTrusteesSucceed() public {
        address wallet = makeAddr("three-trustees");
        addBeneficiary(keys(trustee1Key, trustee2Key, trustee3Key), ZKT, wallet);
        assertTrue(vault.beneficiaries(ZKT, wallet).active);
    }

    function test_governance_signaturesForOtherParamsRevert() public {
        bytes32 idHash = keccak256("id");
        (uint256 n, uint256 d) = nextGov();
        bytes[] memory sigs = govSigs(
            ACTION_ADD_BENEFICIARY, keccak256(abi.encode(ZKT, makeAddr("approved"), idHash)), n, d, twoTrustees()
        );
        vm.expectRevert(IAmanahVault.NotTrustee.selector);
        vault.addBeneficiary(ZKT, attacker, idHash, n, d, sigs);
    }

    function test_governance_signaturesForOtherActionRevert() public {
        vm.prank(guardian);
        vault.pause();
        (uint256 n, uint256 d) = nextGov();
        // Trustees signed lowerPosture(0); someone submits the signatures to unpause.
        bytes[] memory sigs = govSigs(ACTION_LOWER_POSTURE, keccak256(abi.encode(uint8(0))), n, d, twoTrustees());
        vm.expectRevert(IAmanahVault.NotTrustee.selector);
        vault.unpause(n, d, sigs);
    }

    function test_governance_inactiveTrusteeCannotSign() public {
        setSignerActive(trustee3, false);
        assertEq(vault.activeTrustees(), 2);
        vm.expectRevert(IAmanahVault.InactiveSigner.selector);
        addBeneficiary(keys(trustee1Key, trustee3Key), ZKT, makeAddr("late"));
    }

    // Registry

    function test_registerSigner_storesAndEmits() public {
        (uint256 n, uint256 d) = nextGov();
        bytes32 paramsHash =
            keccak256(abi.encode(claudeAuditor, IAmanahVault.Role.AUDITOR, L.LINEAGE_CLAUDE, L.VIEW_CASEFILE));
        bytes[] memory sigs = govSigs(ACTION_REGISTER_SIGNER, paramsHash, n, d, twoTrustees());
        vm.expectEmit(address(vault));
        emit IAmanahVault.SignerRegistered(
            claudeAuditor, uint8(IAmanahVault.Role.AUDITOR), L.LINEAGE_CLAUDE, L.VIEW_CASEFILE
        );
        vault.registerSigner(claudeAuditor, IAmanahVault.Role.AUDITOR, L.LINEAGE_CLAUDE, L.VIEW_CASEFILE, n, d, sigs);

        IAmanahVault.Signer memory s = vault.signers(claudeAuditor);
        assertEq(uint8(s.role), uint8(IAmanahVault.Role.AUDITOR));
        assertEq(s.lineage, L.LINEAGE_CLAUDE);
        assertEq(s.evidenceView, L.VIEW_CASEFILE);
        assertTrue(s.active);
    }

    function test_registerSigner_rejectsKnownKeysRoleNoneAndZero() public {
        vm.expectRevert(IAmanahVault.DuplicateSigner.selector);
        registerSigner(planner, IAmanahVault.Role.AUDITOR, L.LINEAGE_QWEN, L.VIEW_CASEFILE);

        vm.expectRevert(IAmanahVault.DuplicateSigner.selector);
        registerSigner(trustee1, IAmanahVault.Role.PLANNER, L.LINEAGE_CLAUDE, L.VIEW_CONVERSATION);

        vm.expectRevert(AmanahVault.InvalidRole.selector);
        registerSigner(attacker, IAmanahVault.Role.NONE, L.LINEAGE_QWEN, L.VIEW_CASEFILE);

        vm.expectRevert(AmanahVault.ZeroAddress.selector);
        registerSigner(address(0), IAmanahVault.Role.AUDITOR, L.LINEAGE_QWEN, L.VIEW_CASEFILE);
    }

    function test_registerSigner_byPlannerReverts() public {
        vm.expectRevert(IAmanahVault.NotTrustee.selector);
        registerSigner(
            keys(plannerKey, trustee1Key),
            Registration(attacker, IAmanahVault.Role.AUDITOR, L.LINEAGE_QWEN, L.VIEW_CASEFILE)
        );
    }

    function test_setSignerActive_emitsAndUnknownKeyReverts() public {
        vm.expectEmit(address(vault));
        emit IAmanahVault.SignerActiveSet(auditor, false);
        setSignerActive(auditor, false);
        assertFalse(vault.signers(auditor).active);

        vm.expectRevert(IAmanahVault.UnknownSigner.selector);
        setSignerActive(attacker, false);
    }

    function test_setSignerActive_keepsTwoActiveTrustees() public {
        setSignerActive(trustee3, false);
        vm.expectRevert(AmanahVault.TooFewTrustees.selector);
        setSignerActive(trustee2, false);
        setSignerActive(trustee3, true);
        assertEq(vault.activeTrustees(), 3);
    }

    function test_trusteeRotation() public {
        (address trustee4, uint256 trustee4Key) = makeAddrAndKey("trustee4");
        registerSigner(trustee4, IAmanahVault.Role.TRUSTEE, L.LINEAGE_HUMAN, L.VIEW_HUMAN);
        assertEq(vault.activeTrustees(), 4);
        setSignerActive(trustee3, false);
        assertEq(vault.activeTrustees(), 3);
        addBeneficiary(keys(trustee4Key, trustee2Key), ZKT, makeAddr("rotated"));
    }

    // Mandates and beneficiaries

    function test_setMandate_storesAndEmits() public {
        IAmanahVault.Mandate memory m = mandate(250, 1000, 5000, 750);
        (uint256 n, uint256 d) = nextGov();
        bytes[] memory sigs = govSigs(ACTION_SET_MANDATE, keccak256(abi.encode(ZKT, m)), n, d, twoTrustees());
        vm.expectEmit(address(vault));
        emit IAmanahVault.MandateSet(ZKT, m);
        vault.setMandate(ZKT, m, n, d, sigs);

        IAmanahVault.Mandate memory stored = vault.mandates(ZKT);
        assertEq(stored.cap, m.cap);
        assertEq(stored.hardCeiling, m.hardCeiling);
        assertEq(stored.dailyBudget, m.dailyBudget);
        assertEq(stored.perBeneficiaryCap, m.perBeneficiaryCap);
        assertEq(stored.expiry, m.expiry);
        assertEq(stored.purposeHash, m.purposeHash);
        assertTrue(stored.active);
    }

    function test_setMandate_capAboveHardCeilingReverts() public {
        vm.expectRevert(IAmanahVault.AboveHardCeiling.selector);
        setMandate(ZKT, mandate(1501, 1500, 2500, 400));
    }

    function test_addBeneficiary_startsCoolingOff() public {
        address wallet = makeAddr("new-household");
        bytes32 idHash = keccak256(abi.encode("id", wallet));
        uint64 activeFrom = uint64(block.timestamp) + COOLING_OFF;
        vm.expectEmit(address(vault));
        emit IAmanahVault.BeneficiaryAdded(ZKT, wallet, idHash, activeFrom);
        addBeneficiary(ZKT, wallet);

        IAmanahVault.Beneficiary memory b = vault.beneficiaries(ZKT, wallet);
        assertEq(b.idHash, idHash);
        assertEq(b.activeFrom, activeFrom);
        assertTrue(b.active);
    }

    /// A3: the planner key calling addBeneficiary with its own signature reverts with NotTrustee.
    function test_addBeneficiary_byPlannerReverts() public {
        vm.prank(planner);
        vm.expectRevert(IAmanahVault.NotTrustee.selector);
        addBeneficiary(keys(plannerKey), ZKT, makeAddr("planner-friend"));

        vm.prank(planner);
        vm.expectRevert(IAmanahVault.NotTrustee.selector);
        addBeneficiary(keys(trustee1Key, plannerKey), ZKT, makeAddr("planner-friend"));
    }

    function test_addBeneficiary_zeroWalletReverts() public {
        vm.expectRevert(AmanahVault.ZeroAddress.selector);
        addBeneficiary(ZKT, address(0));
    }

    function test_cancelBeneficiary_duringCoolingOff() public {
        address byTrustee = makeAddr("cancelled-by-trustee");
        address byGuardian = makeAddr("cancelled-by-guardian");
        addBeneficiary(ZKT, byTrustee);
        addBeneficiary(ZKT, byGuardian);

        vm.expectEmit(address(vault));
        emit IAmanahVault.BeneficiaryCancelled(ZKT, byTrustee, trustee2);
        vm.prank(trustee2);
        vault.cancelBeneficiary(ZKT, byTrustee);
        vm.prank(guardian);
        vault.cancelBeneficiary(ZKT, byGuardian);
        assertFalse(vault.beneficiaries(ZKT, byTrustee).active);

        vm.warp(block.timestamp + COOLING_OFF);
        IAmanahVault.Payout memory p = payout(ZKT, byGuardian, 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        vm.expectRevert(IAmanahVault.NotAllowlisted.selector);
        vault.execute(p, sigs);
    }

    function test_cancelBeneficiary_afterCoolingOffReverts() public {
        vm.prank(trustee1);
        vm.expectRevert(IAmanahVault.NotInCoolingOff.selector);
        vault.cancelBeneficiary(ZKT, allowlisted[ZKT][0]);
    }

    function test_cancelBeneficiary_onlyTrusteeOrGuardian() public {
        address wallet = makeAddr("new-household");
        addBeneficiary(ZKT, wallet);
        vm.prank(planner);
        vm.expectRevert(IAmanahVault.NotTrustee.selector);
        vault.cancelBeneficiary(ZKT, wallet);

        vm.prank(trustee1);
        vm.expectRevert(IAmanahVault.NotAllowlisted.selector);
        vault.cancelBeneficiary(ZKT, makeAddr("never-added"));
    }

    // Pause

    /// A3: pause reverts a payout, and unpause needs two trustees.
    function test_pause_blocksPayoutsUntilTwoTrusteesUnpause() public {
        vm.prank(guardian);
        vault.pause();
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        vm.expectRevert(Pausable.EnforcedPause.selector);
        vault.execute(p, sigs);

        vm.expectRevert(IAmanahVault.QuorumIncomplete.selector);
        unpause(keys(trustee1Key));
        unpause(keys(trustee2Key, trustee3Key));
        assertFalse(vault.paused());
        vault.execute(p, sigs);
    }

    function test_pause_onlyGuardian() public {
        vm.prank(trustee1);
        vm.expectRevert(IAmanahVault.NotGuardian.selector);
        vault.pause();
        vm.prank(attacker);
        vm.expectRevert(IAmanahVault.NotGuardian.selector);
        vault.pause();
    }

    function test_pause_blocksOverrides() public {
        IAmanahVault.Payout memory p = payout(EDU, allowlisted[EDU][0], 100 * USDC);
        bytes32 anchorId = anchorRefusal(auditor, p);
        bytes[] memory sigs = sigsFor(p, keys(plannerKey, trustee1Key, trustee2Key));
        vm.prank(guardian);
        vault.pause();
        vm.expectRevert(Pausable.EnforcedPause.selector);
        vault.executeOverride(p, anchorId, sigs);
    }

    function test_unpause_whenNotPausedReverts() public {
        vm.expectRevert(Pausable.ExpectedPause.selector);
        unpause(twoTrustees());
    }

    // Fuzz

    /// @dev tierOf against a direct model of plan task A2, for any spend so far today and any amount.
    function testFuzz_tierOf_matchesModel(uint256 spentBefore, uint256 amount) public {
        spentBefore = bound(spentBefore, 0, 2500 * USDC);
        amount = bound(amount, 0, 3000 * USDC);
        // Spread the earlier spend over beneficiaries 0 to 10, at most 400 each, with a trustee co-signing.
        uint256 left = spentBefore;
        for (uint256 i = 0; left > 0; ++i) {
            uint256 chunk = left < 400 * USDC ? left : 400 * USDC;
            IAmanahVault.Payout memory earlier = payout(ZKT, allowlisted[ZKT][i], chunk);
            vault.execute(earlier, elevatedSigs(earlier));
            left -= chunk;
        }
        assertEq(vault.spentToday(ZKT), spentBefore);

        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][11], amount);
        if (amount > 1500 * USDC) {
            vm.expectRevert(IAmanahVault.AboveHardCeiling.selector);
            vault.tierOf(p);
        } else if (spentBefore + amount > 2500 * USDC) {
            vm.expectRevert(IAmanahVault.DailyBudgetExceeded.selector);
            vault.tierOf(p);
        } else if (amount > 400 * USDC) {
            vm.expectRevert(IAmanahVault.BeneficiaryCapExceeded.selector);
            vault.tierOf(p);
        } else {
            bool elevated = amount > 200 * USDC || spentBefore + amount > 2000 * USDC;
            assertEq(vault.tierOf(p), elevated ? 2 : 1);
        }
    }

    function testFuzz_execute_neverPaysAWalletOffTheAllowlist(address wallet) public {
        IAmanahVault.Beneficiary memory b = vault.beneficiaries(ZKT, wallet);
        vm.assume(!b.active);
        IAmanahVault.Payout memory p = payout(ZKT, wallet, 150 * USDC);
        bytes[] memory sigs = routineSigs(p);
        vm.expectRevert(IAmanahVault.NotAllowlisted.selector);
        vault.execute(p, sigs);
    }

    function testFuzz_execute_unregisteredKeyReverts(uint256 key) public {
        key = bound(key, 1, SECP256K1_ORDER - 1);
        vm.assume(vault.signers(vm.addr(key)).role == IAmanahVault.Role.NONE);
        IAmanahVault.Payout memory p = payout(ZKT, allowlisted[ZKT][0], 150 * USDC);
        bytes[] memory sigs = sigsFor(p, keys(plannerKey, auditorKey, key));
        vm.expectRevert(IAmanahVault.UnknownSigner.selector);
        vault.execute(p, sigs);
    }

    function testFuzz_governance_resubmittedWithOtherWalletReverts(address other) public {
        address approved = makeAddr("approved");
        vm.assume(other != approved);
        bytes32 idHash = keccak256("id");
        (uint256 n, uint256 d) = nextGov();
        bytes[] memory sigs =
            govSigs(ACTION_ADD_BENEFICIARY, keccak256(abi.encode(ZKT, approved, idHash)), n, d, twoTrustees());
        vm.expectRevert(IAmanahVault.NotTrustee.selector);
        vault.addBeneficiary(ZKT, other, idHash, n, d, sigs);
    }

    // Helpers

    function anchorRefusal(address refuser, IAmanahVault.Payout memory p) internal returns (bytes32) {
        vm.prank(refuser);
        return vault.anchorDecision(p.proposalId, IAmanahVault.Verdict.REJECT, p.evidenceHash);
    }

    function addrs(address a, address b, address c) internal pure returns (address[] memory r) {
        r = new address[](3);
        (r[0], r[1], r[2]) = (a, b, c);
    }

    function addrs(address a, address b, address c, address d) internal pure returns (address[] memory r) {
        r = new address[](4);
        (r[0], r[1], r[2], r[3]) = (a, b, c, d);
    }
}
