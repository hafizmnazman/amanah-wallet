// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {console} from "forge-std/console.sol";

import {TestUSDC} from "../src/TestUSDC.sol";
import {ScriptBase} from "./ScriptBase.sol";

/// @title DeployToken
/// @notice Deploys the demo's TestUSDC on Base Sepolia (decision A-12), mints the donor's deposit, and writes
/// deployments/<chainId>-token.json. Run it before Deploy.s.sol, then set USDC_ADDRESS to the token it prints:
///
///   set -a; source ../.env; set +a
///   forge script script/DeployToken.s.sol --rpc-url base_sepolia --broadcast --verify
///
/// RELAYER_KEY pays for the deployment and owns the token. The donor is DONOR_KEY's address, else the relayer.
/// TOKEN_MINT_USDC (default 20,000) is minted to the donor: scenario 5 deposits 5,000 into each vault.
contract DeployToken is ScriptBase {
    uint256 internal constant BASE_SEPOLIA = 84532;
    uint256 internal constant ANVIL = 31337;

    function run() external returns (TestUSDC token) {
        if (block.chainid != BASE_SEPOLIA && block.chainid != ANVIL) revert WrongChain(block.chainid);

        uint256 relayerKey = envKey("RELAYER_KEY");
        address owner = vm.addr(relayerKey);
        string memory donorKey = envString("DONOR_KEY");
        address donor = bytes(donorKey).length > 0 ? vm.addr(vm.parseUint(donorKey)) : owner;
        uint256 amount = envUintOr("TOKEN_MINT_USDC", 20_000) * 1e6;

        uint256 deployBlock = block.number;
        vm.startBroadcast(relayerKey);
        token = new TestUSDC(owner);
        token.mint(donor, amount);
        vm.stopBroadcast();

        console.log("TestUSDC", address(token));
        console.log("minted", amount / 1e6, "to the donor", donor);
        console.log("set USDC_ADDRESS in .env to the token above, then run Deploy.s.sol");
        if (broadcasting() && block.chainid != ANVIL) {
            string memory root = "token";
            vm.serializeUint(root, "chainId", block.chainid);
            vm.serializeAddress(root, "token", address(token));
            vm.serializeString(root, "symbol", token.symbol());
            vm.serializeUint(root, "decimals", token.decimals());
            vm.serializeAddress(root, "owner", owner);
            vm.serializeAddress(root, "donor", donor);
            vm.serializeUint(root, "minted", amount);
            string memory json = vm.serializeUint(root, "block", deployBlock);
            vm.createDir("deployments", true);
            string memory path = string.concat("deployments/", vm.toString(block.chainid), "-token.json");
            vm.writeJson(json, path);
            console.log("wrote", path);
        }
    }
}
