// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script} from "forge-std/Script.sol";
import {VmSafe} from "forge-std/Vm.sol";

/// @dev Helpers shared by the deploy and fixture scripts. Values come from the environment; source the
/// repository's .env first (`set -a; source ../.env; set +a`). A variable left empty, as in
/// .env.example, counts as unset.
abstract contract ScriptBase is Script {
    error WrongChain(uint256 chainId);
    error MissingVariable(string name);

    /// @dev Anvil's default accounts, used only when a key is not set and only on a local test chain.
    string internal constant ANVIL_MNEMONIC = "test test test test test test test test test test test junk";
    /// @dev FISCO BCOS's default Web3 chain id (decision E-31). It counts as a local test chain only when
    /// FISCO_LOCAL=1 is set, so a real FISCO network never falls back to the test accounts.
    uint256 internal constant FISCO_WEB3_CHAIN_ID = 20200;

    /// @dev Anvil, or a local FISCO BCOS chain started for testing with FISCO_LOCAL=1.
    function localChain() internal view returns (bool) {
        return block.chainid == 31337 || (block.chainid == FISCO_WEB3_CHAIN_ID && vm.envOr("FISCO_LOCAL", false));
    }

    function envString(string memory name) internal view returns (string memory) {
        return vm.envOr(name, string(""));
    }

    function envUintOr(string memory name, uint256 fallbackValue) internal view returns (uint256) {
        string memory value = envString(name);
        return bytes(value).length == 0 ? fallbackValue : vm.parseUint(value);
    }

    function envKey(string memory name) internal view returns (uint256) {
        string memory value = envString(name);
        if (bytes(value).length == 0) revert MissingVariable(name);
        return vm.parseUint(value);
    }

    /// @dev On a local test chain, an unset key falls back to default account `anvilIndex`.
    function envKeyOrAnvil(string memory name, uint32 anvilIndex) internal view returns (uint256) {
        string memory value = envString(name);
        if (bytes(value).length > 0) return vm.parseUint(value);
        if (!localChain()) revert MissingVariable(name);
        return vm.deriveKey(ANVIL_MNEMONIC, anvilIndex);
    }

    /// @dev The address in `addressName` if set, otherwise the address of the key in `keyName`.
    function envAddressOrKey(string memory addressName, string memory keyName) internal view returns (address) {
        string memory value = envString(addressName);
        if (bytes(value).length > 0) return vm.parseAddress(value);
        return vm.addr(envKey(keyName));
    }

    function sign(uint256 key, bytes32 digest) internal pure returns (bytes memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(key, digest);
        return abi.encodePacked(r, s, v);
    }

    /// @dev True only while forge is broadcasting, so a dry run never writes a deployment file.
    function broadcasting() internal view returns (bool) {
        return vm.isContext(VmSafe.ForgeContext.ScriptBroadcast) || vm.isContext(VmSafe.ForgeContext.ScriptResume);
    }
}
