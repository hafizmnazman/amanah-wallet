// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {console} from "forge-std/console.sol";

import {AmanahVault} from "../src/AmanahVault.sol";
import {ScriptBase} from "./ScriptBase.sol";

/// @title Deploy
/// @notice Deploys AmanahVault to Base Sepolia (plan task A5 and A6) and writes deployments/<chainId>.json.
///
///   set -a; source ../.env; set +a
///   forge script script/Deploy.s.sol --rpc-url "$RPC_URL" --broadcast --verify
///
/// Reads USDC_ADDRESS, TRUSTEE1 to TRUSTEE3 and GUARDIAN as addresses (or derives them from TRUSTEE1_KEY
/// to TRUSTEE3_KEY and GUARDIAN_KEY), COOLING_OFF in seconds (default 600) and RELAYER_KEY, which pays for
/// the deployment and holds no role in the vault. It refuses any chain but Base Sepolia and Anvil.
contract Deploy is ScriptBase {
    uint256 internal constant BASE_SEPOLIA = 84532;
    uint256 internal constant ANVIL = 31337;

    function run() external returns (AmanahVault vault) {
        if (block.chainid != BASE_SEPOLIA && block.chainid != ANVIL) revert WrongChain(block.chainid);

        address usdc = vm.parseAddress(envString("USDC_ADDRESS"));
        address[3] memory trustees = [
            envAddressOrKey("TRUSTEE1", "TRUSTEE1_KEY"),
            envAddressOrKey("TRUSTEE2", "TRUSTEE2_KEY"),
            envAddressOrKey("TRUSTEE3", "TRUSTEE3_KEY")
        ];
        address guardian = envAddressOrKey("GUARDIAN", "GUARDIAN_KEY");
        uint64 coolingOff = uint64(envUintOr("COOLING_OFF", 10 minutes));
        uint256 deployerKey = envKey("RELAYER_KEY");

        uint256 deployBlock = block.number;
        vm.startBroadcast(deployerKey);
        vault = new AmanahVault(usdc, trustees, guardian, coolingOff);
        vm.stopBroadcast();

        console.log("AmanahVault", address(vault));
        console.log("chain", block.chainid, "cooling-off seconds", coolingOff);
        if (broadcasting()) _write(vault, usdc, trustees, guardian, coolingOff, vm.addr(deployerKey), deployBlock);
    }

    function _write(
        AmanahVault vault,
        address usdc,
        address[3] memory trustees,
        address guardian,
        uint64 coolingOff,
        address deployer,
        uint256 deployBlock
    ) internal {
        string memory args = "constructorArgs";
        vm.serializeAddress(args, "usdc", usdc);
        address[] memory list = new address[](3);
        (list[0], list[1], list[2]) = (trustees[0], trustees[1], trustees[2]);
        vm.serializeAddress(args, "trustees", list);
        vm.serializeAddress(args, "guardian", guardian);
        string memory argsJson = vm.serializeUint(args, "coolingOff", coolingOff);

        string memory root = "deployment";
        vm.serializeUint(root, "chainId", block.chainid);
        vm.serializeAddress(root, "vault", address(vault));
        vm.serializeAddress(root, "usdc", usdc);
        vm.serializeUint(root, "block", deployBlock);
        vm.serializeAddress(root, "deployer", deployer);
        string memory json = vm.serializeString(root, "constructorArgs", argsJson);

        vm.createDir("deployments", true);
        string memory path = string.concat("deployments/", vm.toString(block.chainid), ".json");
        vm.writeJson(json, path);
        console.log("wrote", path);
    }
}
