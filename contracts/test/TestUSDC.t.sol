// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Test} from "forge-std/Test.sol";

import {TestUSDC} from "../src/TestUSDC.sol";

/// @dev The Base Sepolia demo token (decision A-12): USDC's decimals, and a mint only its owner can call.
contract TestUSDCTest is Test {
    TestUSDC internal token;
    address internal owner = makeAddr("relayer");
    address internal donor = makeAddr("donor");

    function setUp() public {
        token = new TestUSDC(owner);
    }

    function test_metadata_matchesUsdcDecimals() public view {
        assertEq(token.decimals(), 6);
        assertEq(token.symbol(), "tUSDC");
        assertEq(token.owner(), owner);
        assertEq(token.totalSupply(), 0);
    }

    function test_mint_byOwner() public {
        vm.prank(owner);
        token.mint(donor, 5_000e6);
        assertEq(token.balanceOf(donor), 5_000e6);
    }

    function testFuzz_mint_revertsForAnyoneButTheOwner(address caller) public {
        vm.assume(caller != owner);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, caller));
        vm.prank(caller);
        token.mint(caller, 1);
    }
}
