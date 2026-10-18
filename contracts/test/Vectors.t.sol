// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {AmanahLabels as L} from "../src/AmanahLabels.sol";
import {AmanahVault} from "../src/AmanahVault.sol";
import {IAmanahVault} from "../src/IAmanahVault.sol";

/// @dev EIP-712 vectors for lane B's cross-check (plan task B2). The vault is placed at a fixed address on
/// chain 84532 so the digests never change with the bytecode. Signing keys are keccak256 of public labels,
/// for example keccak256("amanah.vector.planner"), so the file holds no secret.
///
/// test_vectorsMatchSharedFile checks shared/vectors.json against the vault on every run.
/// Regenerate it after a change to the types:  WRITE_VECTORS=true forge test --match-test test_writeVectors
contract VectorsTest is Test {
    string internal constant PATH = "../shared/vectors.json";
    address internal constant VAULT = 0xa3A1000000000000000000000000000000000001;
    uint256 internal constant CHAIN_ID = 84532;
    uint256 internal constant DEADLINE = 1_792_300_000;

    AmanahVault internal vault;
    uint256 internal plannerKey = uint256(keccak256("amanah.vector.planner"));
    uint256 internal trusteeKey = uint256(keccak256("amanah.vector.trustee1"));

    bytes32 internal programmeId = keccak256("amanah.vector.programme");
    address internal auditorKeyAddress = vm.addr(uint256(keccak256("amanah.vector.auditor")));
    address internal wallet = vm.addr(uint256(keccak256("amanah.vector.beneficiary")));

    function setUp() public {
        vm.chainId(CHAIN_ID);
        address[3] memory trustees = [vm.addr(trusteeKey), makeAddr("t2"), makeAddr("t3")];
        deployCodeTo("AmanahVault.sol:AmanahVault", abi.encode(address(1), trustees, makeAddr("guardian"), 600), VAULT);
        vault = AmanahVault(VAULT);
    }

    function test_writeVectors() public {
        if (!vm.envOr("WRITE_VECTORS", false)) return;
        string memory root = "root";
        vm.serializeString(root, "note", "EIP-712 vectors for AmanahVault. Keys are keccak256 of the label shown.");
        vm.serializeString(root, "domain", _domainJson());
        vm.serializeBytes32(root, "domainSeparator", _domainSeparator());
        vm.serializeString(root, "typeHashes", _typeHashesJson());
        vm.serializeString(root, "payout", _payoutJson());
        string memory json = vm.serializeString(root, "governance", _governanceJson());
        vm.writeJson(json, PATH);
    }

    function test_vectorsMatchSharedFile() public view {
        string memory json = vm.readFile(PATH);
        assertEq(vm.parseJsonUint(json, ".domain.chainId"), CHAIN_ID);
        assertEq(vm.parseJsonAddress(json, ".domain.verifyingContract"), VAULT);
        assertEq(vm.parseJsonBytes32(json, ".domainSeparator"), _domainSeparator());
        assertEq(vm.parseJsonBytes32(json, ".typeHashes.Payout"), vault.PAYOUT_TYPEHASH());
        assertEq(vm.parseJsonBytes32(json, ".typeHashes.Governance"), vault.GOVERNANCE_TYPEHASH());

        IAmanahVault.Payout memory p = _payout();
        assertEq(vm.parseJsonBytes32(json, ".payout.message.proposalId"), p.proposalId);
        assertEq(vm.parseJsonUint(json, ".payout.message.amount"), p.amount);
        assertEq(vm.parseJsonBytes32(json, ".payout.digest"), vault.hashPayout(p));
        assertEq(vm.parseJsonBytes(json, ".payout.signature"), _sign(plannerKey, vault.hashPayout(p)));

        string[6] memory actions = _actionNames();
        bytes32[6] memory paramsHashes = _paramsHashes();
        for (uint256 i = 0; i < actions.length; ++i) {
            string memory at = string.concat(".governance.", actions[i]);
            bytes32 digest = vault.hashGovernance(keccak256(bytes(actions[i])), paramsHashes[i], i + 1, DEADLINE);
            assertEq(vm.parseJsonBytes32(json, string.concat(at, ".paramsHash")), paramsHashes[i]);
            assertEq(vm.parseJsonBytes32(json, string.concat(at, ".digest")), digest);
            assertEq(vm.parseJsonBytes(json, string.concat(at, ".signature")), _sign(trusteeKey, digest));
        }
    }

    // The fixed payout and governance calls

    function _payout() internal view returns (IAmanahVault.Payout memory) {
        return IAmanahVault.Payout({
            proposalId: keccak256("amanah.vector.proposal"),
            programmeId: programmeId,
            beneficiary: wallet,
            amount: 150_000_000,
            evidenceHash: keccak256("amanah.vector.evidence"),
            nonce: 42,
            deadline: DEADLINE
        });
    }

    function _mandate() internal pure returns (IAmanahVault.Mandate memory) {
        return IAmanahVault.Mandate({
            cap: 200_000_000,
            hardCeiling: 1_500_000_000,
            dailyBudget: 2_500_000_000,
            perBeneficiaryCap: 400_000_000,
            expiry: 1_823_836_000,
            purposeHash: keccak256("amanah.vector.purpose"),
            active: true
        });
    }

    function _actionNames() internal pure returns (string[6] memory) {
        return ["lowerPosture", "registerSigner", "setSignerActive", "setMandate", "addBeneficiary", "unpause"];
    }

    /// @dev paramsHash = keccak256(abi.encode(params in declaration order)), per plan section 3.2.
    function _paramsHashes() internal view returns (bytes32[6] memory h) {
        h[0] = keccak256(abi.encode(uint8(0)));
        h[1] = keccak256(abi.encode(auditorKeyAddress, IAmanahVault.Role.AUDITOR, L.LINEAGE_QWEN, L.VIEW_CASEFILE));
        h[2] = keccak256(abi.encode(auditorKeyAddress, false));
        h[3] = keccak256(abi.encode(programmeId, _mandate()));
        h[4] = keccak256(abi.encode(programmeId, wallet, keccak256("amanah.vector.idHash")));
        h[5] = keccak256(abi.encode());
    }

    // JSON

    function _domainJson() internal returns (string memory) {
        string memory o = "domain";
        vm.serializeString(o, "name", "AmanahVault");
        vm.serializeString(o, "version", "1");
        vm.serializeUint(o, "chainId", CHAIN_ID);
        return vm.serializeAddress(o, "verifyingContract", VAULT);
    }

    function _typeHashesJson() internal returns (string memory) {
        string memory o = "typeHashes";
        vm.serializeBytes32(o, "Payout", vault.PAYOUT_TYPEHASH());
        return vm.serializeBytes32(o, "Governance", vault.GOVERNANCE_TYPEHASH());
    }

    function _payoutJson() internal returns (string memory) {
        IAmanahVault.Payout memory p = _payout();
        string memory m = "payoutMessage";
        vm.serializeBytes32(m, "proposalId", p.proposalId);
        vm.serializeBytes32(m, "programmeId", p.programmeId);
        vm.serializeAddress(m, "beneficiary", p.beneficiary);
        vm.serializeString(m, "amount", vm.toString(p.amount));
        vm.serializeBytes32(m, "evidenceHash", p.evidenceHash);
        vm.serializeString(m, "nonce", vm.toString(p.nonce));
        string memory message = vm.serializeString(m, "deadline", vm.toString(p.deadline));

        bytes32 digest = vault.hashPayout(p);
        string memory o = "payout";
        vm.serializeString(o, "message", message);
        vm.serializeBytes32(o, "digest", digest);
        vm.serializeString(o, "signerKeyLabel", "amanah.vector.planner");
        vm.serializeAddress(o, "signer", vm.addr(plannerKey));
        return vm.serializeBytes(o, "signature", _sign(plannerKey, digest));
    }

    function _governanceJson() internal returns (string memory json) {
        string[6] memory actions = _actionNames();
        bytes32[6] memory paramsHashes = _paramsHashes();
        string[6] memory params = [
            "level=0",
            "key=address of keccak256('amanah.vector.auditor'), role=AUDITOR (2), lineage=keccak256('alibaba/qwen'), evidenceView=keccak256('casefile')",
            "key=address of keccak256('amanah.vector.auditor'), active=false",
            "programmeId=keccak256('amanah.vector.programme'), mandate as in setMandateMandate",
            "programmeId=keccak256('amanah.vector.programme'), wallet=address of keccak256('amanah.vector.beneficiary'), idHash=keccak256('amanah.vector.idHash')",
            "no parameters: keccak256 of empty bytes"
        ];
        for (uint256 i = 0; i < actions.length; ++i) {
            bytes32 digest = vault.hashGovernance(keccak256(bytes(actions[i])), paramsHashes[i], i + 1, DEADLINE);
            string memory o = actions[i];
            vm.serializeString(o, "params", params[i]);
            vm.serializeBytes32(o, "action", keccak256(bytes(actions[i])));
            vm.serializeBytes32(o, "paramsHash", paramsHashes[i]);
            vm.serializeString(o, "govNonce", vm.toString(i + 1));
            vm.serializeString(o, "deadline", vm.toString(DEADLINE));
            vm.serializeBytes32(o, "digest", digest);
            vm.serializeString(o, "signerKeyLabel", "amanah.vector.trustee1");
            vm.serializeAddress(o, "signer", vm.addr(trusteeKey));
            string memory entry = vm.serializeBytes(o, "signature", _sign(trusteeKey, digest));
            json = vm.serializeString("governance", actions[i], entry);
        }
        IAmanahVault.Mandate memory m = _mandate();
        string memory mo = "mandate";
        vm.serializeString(mo, "cap", vm.toString(m.cap));
        vm.serializeString(mo, "hardCeiling", vm.toString(m.hardCeiling));
        vm.serializeString(mo, "dailyBudget", vm.toString(m.dailyBudget));
        vm.serializeString(mo, "perBeneficiaryCap", vm.toString(m.perBeneficiaryCap));
        vm.serializeString(mo, "expiry", vm.toString(m.expiry));
        vm.serializeBytes32(mo, "purposeHash", m.purposeHash);
        string memory mandateJson = vm.serializeBool(mo, "active", m.active);
        json = vm.serializeString("governance", "setMandateMandate", mandateJson);
    }

    function _domainSeparator() internal view returns (bytes32) {
        return keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256("AmanahVault"),
                keccak256("1"),
                CHAIN_ID,
                VAULT
            )
        );
    }

    function _sign(uint256 key, bytes32 digest) internal pure returns (bytes memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(key, digest);
        return abi.encodePacked(r, s, v);
    }
}
