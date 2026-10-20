// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {VaultHandler} from "./invariant/VaultHandler.sol";

/// @dev Plan task A4. Each invariant asserts that one class of success the rules forbid never happened,
/// across random call sequences (runs and depth in foundry.toml). The handler's own records are the
/// reference, so a bug in the vault's accounting cannot hide itself.
contract InvariantTest is Test {
    VaultHandler internal handler;

    function setUp() public {
        vm.warp(1_792_300_000);
        handler = new VaultHandler();

        bytes4[] memory selectors = new bytes4[](23);
        selectors[0] = VaultHandler.execute.selector;
        selectors[1] = VaultHandler.execute.selector;
        selectors[2] = VaultHandler.execute.selector;
        selectors[3] = VaultHandler.executeOverride.selector;
        selectors[4] = VaultHandler.replay.selector;
        selectors[5] = VaultHandler.anchor.selector;
        selectors[6] = VaultHandler.setMandate.selector;
        selectors[7] = VaultHandler.addBeneficiary.selector;
        selectors[8] = VaultHandler.setSignerActive.selector;
        selectors[9] = VaultHandler.registerSigner.selector;
        selectors[10] = VaultHandler.lowerPosture.selector;
        selectors[11] = VaultHandler.unpause.selector;
        selectors[12] = VaultHandler.pause.selector;
        selectors[13] = VaultHandler.raisePosture.selector;
        selectors[14] = VaultHandler.warp.selector;
        selectors[15] = VaultHandler.cancelBeneficiary.selector;
        selectors[16] = VaultHandler.execute.selector;
        selectors[17] = VaultHandler.unpause.selector;
        selectors[18] = VaultHandler.executeBatch.selector;
        selectors[19] = VaultHandler.executeBatch.selector;
        selectors[20] = VaultHandler.overrideAgain.selector;
        selectors[21] = VaultHandler.anchorReport.selector;
        selectors[22] = VaultHandler.retireTrustee.selector;
        targetSelector(FuzzSelector({addr: address(handler), selectors: selectors}));
        targetContract(address(handler));
    }

    /// USDC leaves the vault only to beneficiaries allowlisted for that programme and past cooling-off,
    /// and only through the payouts the handler saw succeed.
    function invariant_onlyAllowlisted() public view {
        assertEq(handler.badRecipient(), 0, "paid a wallet that was not allowlisted and past cooling-off");
        assertEq(
            handler.usdc().balanceOf(address(handler.vault())) + handler.paidOut(),
            handler.INITIAL_BALANCE(),
            "USDC left the vault outside a recorded payout"
        );
    }

    /// No programme spends more than its daily budget in a day, and nothing is paid outside an active
    /// mandate or above the hard ceiling.
    function invariant_dailyBudget() public view {
        assertEq(handler.overBudget(), 0, "a day's spend passed the daily budget");
        assertEq(handler.outsideMandate(), 0, "paid outside an active mandate or above the hard ceiling");
    }

    /// Spend whose signer set held no trustee stays at or under 80% of each daily budget per day, and
    /// machine signers alone never pay above the cap or while the posture is raised.
    function invariant_machineBound() public view {
        assertEq(handler.overMachineLine(), 0, "machine-only spend passed 80% of a daily budget");
        assertEq(handler.machineElevated(), 0, "machine-only payout above the cap or under raised posture");
    }

    /// No beneficiary receives more than its programme's cap within a period.
    function invariant_perBeneficiaryCap() public view {
        assertEq(handler.overBeneficiaryCap(), 0, "a beneficiary passed its period cap");
    }

    /// Every executed non-override payout had a planner and an auditor of different lineages.
    function invariant_lineageDistinct() public view {
        assertEq(handler.sameLineage(), 0, "planner and auditor shared a lineage");
    }

    /// Posture rose only through the posture oracle and fell only through lowerPosture with two trustees.
    function invariant_postureMonotone() public view {
        assertEq(handler.illegalPosture(), 0, "posture moved without a legitimate raise or two-trustee lowering");
        assertEq(handler.vault().posture(), handler.ghostPosture());
    }

    /// Every payout nonce and every governance nonce executed at most once.
    function invariant_noReplay() public view {
        assertEq(handler.replays(), 0, "a nonce executed twice");
    }

    /// Governance needed two distinct active trustees, overrides cited an unused auditor or sentinel
    /// refusal, single-key actions came from the right key, and nothing was paid while paused.
    function invariant_authority() public view {
        assertEq(handler.badAuthority(), 0, "an action succeeded without the authority it needs");
        assertEq(handler.badOverride(), 0, "an override succeeded without a valid refusal and two trustees");
        assertEq(handler.paidWhilePaused(), 0, "paid while paused");
    }

    /// Each anchored refusal justified at most one override, even when cited again with a fresh nonce and
    /// two trustees, and the vault marks every refusal an override cited.
    function invariant_refusalCitedOnce() public view {
        assertEq(handler.refusalCitedTwice(), 0, "a refusal anchor justified a second override");
        assertEq(handler.citedButUnmarked(), 0, "an override cited a refusal the vault does not mark as used");
    }

    /// The vault's count of active trustees matches the handler's registry after every call and never drops
    /// below two, so two trustees can always sign governance.
    function invariant_trusteeCount() public view {
        assertEq(handler.trusteeCountDrift(), 0, "the trustee count was wrong or under two after a call");
        assertEq(handler.vault().activeTrustees(), handler.ghostActiveTrustees(), "trustee count drifted");
        assertGe(handler.vault().activeTrustees(), 2, "fewer than two active trustees");
    }

    /// The last report hash moved only through the active posture oracle, by anchorReport or raisePosture.
    function invariant_reportOracleOnly() public view {
        assertEq(handler.illegalReport(), 0, "the report hash changed without the active posture oracle");
        assertEq(handler.vault().lastReportHash(), handler.ghostReportHash());
    }

    /// With INVARIANT_STATS=true, appends what each run did to cache/invariant-stats.txt, to show the
    /// invariants were checked against a vault that moved money.
    function afterInvariant() external {
        if (!vm.envOr("INVARIANT_STATS", false)) return;
        vm.writeLine(
            "cache/invariant-stats.txt",
            string.concat(
                "stats payouts=",
                vm.toString(handler.payouts()),
                " overrides=",
                vm.toString(handler.overrides()),
                " governance=",
                vm.toString(handler.governanceSuccesses()),
                " paid_usdc=",
                vm.toString(handler.paidOut() / 1e6),
                " recite_attempts=",
                vm.toString(handler.reciteAttempts()),
                " reports=",
                vm.toString(handler.reportsAnchored())
            )
        );
    }
}
