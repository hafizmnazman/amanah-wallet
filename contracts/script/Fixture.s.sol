// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {console} from "forge-std/console.sol";

import {AmanahLabels as L} from "../src/AmanahLabels.sol";
import {AmanahVault} from "../src/AmanahVault.sol";
import {IAmanahVault} from "../src/IAmanahVault.sol";
import {MockUSDC} from "../src/mocks/MockUSDC.sol";
import {ScriptBase} from "./ScriptBase.sol";

/// @title Fixture
/// @notice Anvil only (plan task A5). Deploys MockUSDC and a vault with a 60-second cooling-off, registers
/// the planner, auditor, sentinel, posture oracle and a Claude-lineage control auditor (for scenario 11),
/// sets the programme mandates, allowlists the demo beneficiaries, mints 100,000 USDC to the vault and
/// writes deployments/31337.json.
///
///   anvil
///   forge script script/Fixture.s.sol --rpc-url http://127.0.0.1:8545 --broadcast
///
/// Keys come from PLANNER_KEY, AUDITOR_KEY, SENTINEL_KEY, POSTURE_ORACLE_KEY, CONTROL_AUDITOR_KEY,
/// TRUSTEE1_KEY to TRUSTEE3_KEY and GUARDIAN_KEY, each falling back to an Anvil default account
/// (indexes in docs/PATHS.md). Anvil account 0 pays for everything. Data comes from ../redteam/data when
/// lane C has written it, otherwise from test/fixtures; the format is in shared/fixture-data.md.
contract Fixture is ScriptBase {
    uint64 internal constant COOLING_OFF = 60;
    uint256 internal constant USDC = 1e6;
    uint256 internal constant VAULT_FUNDS = 100_000 * USDC;

    AmanahVault internal vault;
    MockUSDC internal usdc;
    uint256 internal trustee1Key;
    uint256 internal trustee2Key;
    uint256 internal govNonce;
    string internal dataDir;

    mapping(bytes32 codeHash => bytes32 programmeId) internal programmeOf;
    string[] internal codes;
    uint256 internal beneficiaryCount;

    function run() external {
        if (block.chainid != 31337) revert WrongChain(block.chainid);
        // Foundry refuses to read ../redteam/data until that folder exists, so try it and fall back.
        dataDir = "test/fixtures";
        try vm.readFile("../redteam/data/mandates.json") returns (string memory) {
            dataDir = "../redteam/data";
        } catch {}

        trustee1Key = envKeyOrAnvil("TRUSTEE1_KEY", 5);
        trustee2Key = envKeyOrAnvil("TRUSTEE2_KEY", 6);
        address[3] memory trustees =
            [vm.addr(trustee1Key), vm.addr(trustee2Key), vm.addr(envKeyOrAnvil("TRUSTEE3_KEY", 7))];
        address guardian = vm.addr(envKeyOrAnvil("GUARDIAN_KEY", 8));

        vm.startBroadcast(vm.deriveKey(ANVIL_MNEMONIC, 0));
        usdc = new MockUSDC();
        vault = new AmanahVault(address(usdc), trustees, guardian, COOLING_OFF);
        _registerSigners();
        _setMandates();
        _addBeneficiaries();
        usdc.mint(address(vault), VAULT_FUNDS);
        vm.stopBroadcast();

        console.log("AmanahVault", address(vault));
        console.log("MockUSDC", address(usdc));
        console.log("data from", dataDir);
        console.log("programmes", codes.length, "beneficiaries", beneficiaryCount);
        if (broadcasting()) _write(trustees, guardian);
    }

    function _registerSigners() internal {
        // The planner's family, Claude unless PLANNER_LINEAGE names another (decision E-30). The control auditor
        // shares it, so scenario 11's two keys of one family still revert with SameLineage.
        bytes32 plannerLineage = keccak256(bytes(vm.envOr("PLANNER_LINEAGE", string("anthropic/claude"))));
        _register("PLANNER_KEY", 1, IAmanahVault.Role.PLANNER, plannerLineage, L.VIEW_CONVERSATION);
        _register("AUDITOR_KEY", 2, IAmanahVault.Role.AUDITOR, L.LINEAGE_QWEN, L.VIEW_CASEFILE);
        _register("SENTINEL_KEY", 3, IAmanahVault.Role.SENTINEL, L.LINEAGE_RULES, L.VIEW_NUMBERS);
        _register("POSTURE_ORACLE_KEY", 4, IAmanahVault.Role.POSTURE_ORACLE, L.LINEAGE_GPT, L.VIEW_NUMBERS);
        _register("CONTROL_AUDITOR_KEY", 9, IAmanahVault.Role.AUDITOR, plannerLineage, L.VIEW_CASEFILE);
    }

    function _register(
        string memory keyName,
        uint32 anvilIndex,
        IAmanahVault.Role role,
        bytes32 lineage,
        bytes32 evidenceView
    ) internal {
        address key = vm.addr(envKeyOrAnvil(keyName, anvilIndex));
        (uint256 n, uint256 d, bytes[] memory sigs) =
            _gov(vault.ACTION_REGISTER_SIGNER(), keccak256(abi.encode(key, role, lineage, evidenceView)));
        vault.registerSigner(key, role, lineage, evidenceView, n, d, sigs);
        // Checkers anchor their own decisions, so they need gas on Anvil.
        if (key.balance < 1 ether) payable(key).transfer(10 ether);
    }

    function _setMandates() internal {
        string memory json = vm.readFile(string.concat(dataDir, "/mandates.json"));
        for (uint256 i = 0; vm.keyExistsJson(json, _at("programmes", i)); ++i) {
            string memory at = _at("programmes", i);
            string memory code = vm.parseJsonString(json, string.concat(at, ".code"));
            bytes32 programmeId = vm.parseJsonBytes32(json, string.concat(at, ".programme_id"));
            IAmanahVault.Mandate memory m = IAmanahVault.Mandate({
                cap: vm.parseJsonUint(json, string.concat(at, ".cap_usdc")) * USDC,
                hardCeiling: vm.parseJsonUint(json, string.concat(at, ".hard_ceiling_usdc")) * USDC,
                dailyBudget: vm.parseJsonUint(json, string.concat(at, ".daily_budget_usdc")) * USDC,
                perBeneficiaryCap: vm.parseJsonUint(json, string.concat(at, ".per_beneficiary_cap_usdc")) * USDC,
                expiry: uint64(block.timestamp + 365 days),
                purposeHash: vm.parseJsonBytes32(json, string.concat(at, ".purpose_hash")),
                active: true
            });
            (uint256 n, uint256 d, bytes[] memory sigs) =
                _gov(vault.ACTION_SET_MANDATE(), keccak256(abi.encode(programmeId, m)));
            vault.setMandate(programmeId, m, n, d, sigs);
            programmeOf[keccak256(bytes(code))] = programmeId;
            codes.push(code);
        }
    }

    function _addBeneficiaries() internal {
        string memory json = vm.readFile(string.concat(dataDir, "/beneficiaries.json"));
        for (uint256 i = 0; vm.keyExistsJson(json, _at("beneficiaries", i)); ++i) {
            string memory at = _at("beneficiaries", i);
            string memory code = vm.parseJsonString(json, string.concat(at, ".programme_code"));
            bytes32 programmeId = programmeOf[keccak256(bytes(code))];
            address wallet = vm.parseJsonAddress(json, string.concat(at, ".wallet"));
            bytes32 idHash = vm.parseJsonBytes32(json, string.concat(at, ".id_hash"));
            (uint256 n, uint256 d, bytes[] memory sigs) =
                _gov(vault.ACTION_ADD_BENEFICIARY(), keccak256(abi.encode(programmeId, wallet, idHash)));
            vault.addBeneficiary(programmeId, wallet, idHash, n, d, sigs);
            ++beneficiaryCount;
        }
    }

    /// @dev Trustees 1 and 2 sign each governance call.
    function _gov(bytes32 action, bytes32 paramsHash) internal returns (uint256 n, uint256 d, bytes[] memory sigs) {
        n = ++govNonce;
        d = block.timestamp + 1 hours;
        bytes32 digest = vault.hashGovernance(action, paramsHash, n, d);
        sigs = new bytes[](2);
        sigs[0] = sign(trustee1Key, digest);
        sigs[1] = sign(trustee2Key, digest);
    }

    function _write(address[3] memory trustees, address guardian) internal {
        string memory s = "signers";
        vm.serializeAddress(s, "planner", vm.addr(envKeyOrAnvil("PLANNER_KEY", 1)));
        vm.serializeAddress(s, "auditor", vm.addr(envKeyOrAnvil("AUDITOR_KEY", 2)));
        vm.serializeAddress(s, "sentinel", vm.addr(envKeyOrAnvil("SENTINEL_KEY", 3)));
        vm.serializeAddress(s, "postureOracle", vm.addr(envKeyOrAnvil("POSTURE_ORACLE_KEY", 4)));
        vm.serializeAddress(s, "controlAuditor", vm.addr(envKeyOrAnvil("CONTROL_AUDITOR_KEY", 9)));
        address[] memory list = new address[](3);
        (list[0], list[1], list[2]) = (trustees[0], trustees[1], trustees[2]);
        vm.serializeAddress(s, "trustees", list);
        vm.serializeAddress(s, "guardian", guardian);
        string memory signersJson = vm.serializeAddress(s, "relayer", vm.addr(vm.deriveKey(ANVIL_MNEMONIC, 0)));

        string memory p = "programmes";
        string memory programmesJson;
        for (uint256 i = 0; i < codes.length; ++i) {
            programmesJson = vm.serializeBytes32(p, codes[i], programmeOf[keccak256(bytes(codes[i]))]);
        }

        string memory root = "fixture";
        vm.serializeUint(root, "chainId", block.chainid);
        vm.serializeAddress(root, "vault", address(vault));
        vm.serializeAddress(root, "usdc", address(usdc));
        vm.serializeUint(root, "block", block.number);
        vm.serializeUint(root, "coolingOff", COOLING_OFF);
        vm.serializeUint(root, "beneficiaries", beneficiaryCount);
        vm.serializeString(root, "dataDir", dataDir);
        vm.serializeString(root, "signers", signersJson);
        string memory json = vm.serializeString(root, "programmes", programmesJson);

        vm.createDir("deployments", true);
        vm.writeJson(json, "deployments/31337.json");
        console.log("wrote deployments/31337.json");
    }

    function _at(string memory list, uint256 i) internal pure returns (string memory) {
        return string.concat(".", list, "[", vm.toString(i), "]");
    }
}
