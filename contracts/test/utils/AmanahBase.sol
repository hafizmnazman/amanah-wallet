// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {AmanahLabels as L} from "../../src/AmanahLabels.sol";
import {AmanahVault} from "../../src/AmanahVault.sol";
import {IAmanahVault} from "../../src/IAmanahVault.sol";
import {MockUSDC} from "../../src/mocks/MockUSDC.sol";

/// @dev Deploys a vault with the three demo programmes from plan section 10, registers the machine
/// signers and allowlists twelve beneficiaries per programme, all past cooling-off.
///
/// Digests are computed here, independently of the vault, and helpers make exactly one external
/// call, so `vm.expectRevert` placed before a helper applies to the vault call it makes.
abstract contract AmanahBase is Test {
    uint256 internal constant USDC = 1e6;
    uint64 internal constant COOLING_OFF = 10 minutes;
    /// @dev 18 October 2026, so day and period indexes look like the real chain's.
    uint256 internal constant START = 1_792_300_000;

    bytes32 internal constant ZKT = keccak256("ZKT-IPOH-FAKIR-M");
    bytes32 internal constant REL = keccak256("REL-PERAK-FLOOD");
    bytes32 internal constant EDU = keccak256("EDU-BURSARY-S1");
    uint256 internal constant BENEFICIARIES_PER_PROGRAMME = 12;

    bytes32 internal constant DOMAIN_TYPEHASH =
        keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");
    bytes32 internal constant PAYOUT_TYPEHASH = keccak256(
        "Payout(bytes32 proposalId,bytes32 programmeId,address beneficiary,uint256 amount,bytes32 evidenceHash,uint256 nonce,uint256 deadline)"
    );
    bytes32 internal constant GOVERNANCE_TYPEHASH =
        keccak256("Governance(bytes32 action,bytes32 paramsHash,uint256 govNonce,uint256 deadline)");
    bytes32 internal constant ACTION_LOWER_POSTURE = keccak256("lowerPosture");
    bytes32 internal constant ACTION_REGISTER_SIGNER = keccak256("registerSigner");
    bytes32 internal constant ACTION_SET_SIGNER_ACTIVE = keccak256("setSignerActive");
    bytes32 internal constant ACTION_SET_MANDATE = keccak256("setMandate");
    bytes32 internal constant ACTION_ADD_BENEFICIARY = keccak256("addBeneficiary");
    bytes32 internal constant ACTION_UNPAUSE = keccak256("unpause");

    MockUSDC internal usdc;
    AmanahVault internal vault;

    address internal planner;
    uint256 internal plannerKey;
    address internal auditor;
    uint256 internal auditorKey;
    address internal sentinel;
    uint256 internal sentinelKey;
    address internal oracle;
    uint256 internal oracleKey;
    address internal trustee1;
    uint256 internal trustee1Key;
    address internal trustee2;
    uint256 internal trustee2Key;
    address internal trustee3;
    uint256 internal trustee3Key;
    address internal guardian;
    uint256 internal guardianKey;
    /// @dev A second Claude key, unregistered until a test registers it as a same-lineage auditor.
    address internal claudeAuditor;
    uint256 internal claudeAuditorKey;
    address internal attacker;
    uint256 internal attackerKey;

    mapping(bytes32 programmeId => address[]) internal allowlisted;

    uint256 private _nextNonce = 1;
    uint256 private _nextGovNonce = 1;

    function setUp() public virtual {
        vm.warp(START);
        (planner, plannerKey) = makeAddrAndKey("planner");
        (auditor, auditorKey) = makeAddrAndKey("auditor");
        (sentinel, sentinelKey) = makeAddrAndKey("sentinel");
        (oracle, oracleKey) = makeAddrAndKey("posture-oracle");
        (trustee1, trustee1Key) = makeAddrAndKey("trustee1");
        (trustee2, trustee2Key) = makeAddrAndKey("trustee2");
        (trustee3, trustee3Key) = makeAddrAndKey("trustee3");
        (guardian, guardianKey) = makeAddrAndKey("guardian");
        (claudeAuditor, claudeAuditorKey) = makeAddrAndKey("claude-auditor");
        (attacker, attackerKey) = makeAddrAndKey("attacker");

        usdc = new MockUSDC();
        vault = new AmanahVault(address(usdc), [trustee1, trustee2, trustee3], guardian, COOLING_OFF);

        registerSigner(planner, IAmanahVault.Role.PLANNER, L.LINEAGE_CLAUDE, L.VIEW_CONVERSATION);
        registerSigner(auditor, IAmanahVault.Role.AUDITOR, L.LINEAGE_QWEN, L.VIEW_CASEFILE);
        registerSigner(sentinel, IAmanahVault.Role.SENTINEL, L.LINEAGE_RULES, L.VIEW_NUMBERS);
        registerSigner(oracle, IAmanahVault.Role.POSTURE_ORACLE, L.LINEAGE_GPT, L.VIEW_NUMBERS);

        setMandate(ZKT, mandate(200, 1500, 2500, 400));
        setMandate(REL, mandate(300, 2000, 3000, 600));
        setMandate(EDU, mandate(500, 1000, 2000, 500));

        bytes32[3] memory programmes = [ZKT, REL, EDU];
        for (uint256 p = 0; p < programmes.length; ++p) {
            for (uint256 i = 0; i < BENEFICIARIES_PER_PROGRAMME; ++i) {
                address wallet = makeAddr(string.concat(vm.toString(programmes[p]), "-", vm.toString(i)));
                addBeneficiary(programmes[p], wallet);
                allowlisted[programmes[p]].push(wallet);
            }
        }
        vm.warp(block.timestamp + COOLING_OFF);
        usdc.mint(address(vault), 100_000 * USDC);
    }

    // Digests

    function domainSeparator() internal view returns (bytes32) {
        return
            keccak256(
                abi.encode(DOMAIN_TYPEHASH, keccak256("AmanahVault"), keccak256("1"), block.chainid, address(vault))
            );
    }

    function payoutDigest(IAmanahVault.Payout memory p) internal view returns (bytes32) {
        bytes32 structHash = keccak256(
            abi.encode(
                PAYOUT_TYPEHASH,
                p.proposalId,
                p.programmeId,
                p.beneficiary,
                p.amount,
                p.evidenceHash,
                p.nonce,
                p.deadline
            )
        );
        return keccak256(abi.encodePacked("\x19\x01", domainSeparator(), structHash));
    }

    function govDigest(bytes32 action, bytes32 paramsHash, uint256 govNonce, uint256 deadline)
        internal
        view
        returns (bytes32)
    {
        bytes32 structHash = keccak256(abi.encode(GOVERNANCE_TYPEHASH, action, paramsHash, govNonce, deadline));
        return keccak256(abi.encodePacked("\x19\x01", domainSeparator(), structHash));
    }

    // Payouts

    function payout(bytes32 programmeId, address beneficiary, uint256 amount)
        internal
        returns (IAmanahVault.Payout memory p)
    {
        uint256 nonce = _nextNonce++;
        p = IAmanahVault.Payout({
            proposalId: keccak256(abi.encode("proposal", nonce)),
            programmeId: programmeId,
            beneficiary: beneficiary,
            amount: amount,
            evidenceHash: keccak256(abi.encode("evidence", nonce)),
            nonce: nonce,
            deadline: block.timestamp + 1 hours
        });
    }

    function sigsFor(IAmanahVault.Payout memory p, uint256[] memory signerKeys) internal view returns (bytes[] memory) {
        return signAll(payoutDigest(p), signerKeys);
    }

    function routineSigs(IAmanahVault.Payout memory p) internal view returns (bytes[] memory) {
        return sigsFor(p, keys(plannerKey, auditorKey, sentinelKey));
    }

    function elevatedSigs(IAmanahVault.Payout memory p) internal view returns (bytes[] memory) {
        return sigsFor(p, keys(plannerKey, auditorKey, sentinelKey, trustee1Key));
    }

    /// @dev Executes a routine payout to beneficiary `index` of a programme.
    function payRoutine(bytes32 programmeId, uint256 index, uint256 amount)
        internal
        returns (IAmanahVault.Payout memory p)
    {
        p = payout(programmeId, allowlisted[programmeId][index], amount);
        vault.execute(p, routineSigs(p));
    }

    // Governance. The short forms sign with trustees 1 and 2; the `signerKeys` forms sign with any keys.

    struct Registration {
        address key;
        IAmanahVault.Role role;
        bytes32 lineage;
        bytes32 evidenceView;
    }

    function registerSigner(address key, IAmanahVault.Role role, bytes32 lineage, bytes32 evidenceView) internal {
        registerSigner(twoTrustees(), Registration(key, role, lineage, evidenceView));
    }

    function registerSigner(uint256[] memory signerKeys, Registration memory r) internal {
        bytes32 paramsHash = keccak256(abi.encode(r.key, r.role, r.lineage, r.evidenceView));
        (uint256 n, uint256 d, bytes[] memory sigs) = governance(ACTION_REGISTER_SIGNER, paramsHash, signerKeys);
        vault.registerSigner(r.key, r.role, r.lineage, r.evidenceView, n, d, sigs);
    }

    function setSignerActive(address key, bool active) internal {
        bytes32 paramsHash = keccak256(abi.encode(key, active));
        (uint256 n, uint256 d, bytes[] memory sigs) = governance(ACTION_SET_SIGNER_ACTIVE, paramsHash, twoTrustees());
        vault.setSignerActive(key, active, n, d, sigs);
    }

    function setMandate(bytes32 programmeId, IAmanahVault.Mandate memory m) internal {
        bytes32 paramsHash = keccak256(abi.encode(programmeId, m));
        (uint256 n, uint256 d, bytes[] memory sigs) = governance(ACTION_SET_MANDATE, paramsHash, twoTrustees());
        vault.setMandate(programmeId, m, n, d, sigs);
    }

    function addBeneficiary(bytes32 programmeId, address wallet) internal {
        addBeneficiary(twoTrustees(), programmeId, wallet);
    }

    function addBeneficiary(uint256[] memory signerKeys, bytes32 programmeId, address wallet) internal {
        bytes32 idHash = keccak256(abi.encode("id", wallet));
        bytes32 paramsHash = keccak256(abi.encode(programmeId, wallet, idHash));
        (uint256 n, uint256 d, bytes[] memory sigs) = governance(ACTION_ADD_BENEFICIARY, paramsHash, signerKeys);
        vault.addBeneficiary(programmeId, wallet, idHash, n, d, sigs);
    }

    function lowerPosture(uint8 level, uint256[] memory signerKeys) internal {
        (uint256 n, uint256 d, bytes[] memory sigs) =
            governance(ACTION_LOWER_POSTURE, keccak256(abi.encode(level)), signerKeys);
        vault.lowerPosture(level, n, d, sigs);
    }

    function unpause(uint256[] memory signerKeys) internal {
        (uint256 n, uint256 d, bytes[] memory sigs) = governance(ACTION_UNPAUSE, keccak256(abi.encode()), signerKeys);
        vault.unpause(n, d, sigs);
    }

    /// @dev A fresh governance nonce and deadline, and the signatures of `signerKeys` over them.
    function governance(bytes32 action, bytes32 paramsHash, uint256[] memory signerKeys)
        internal
        returns (uint256 govNonce, uint256 deadline, bytes[] memory sigs)
    {
        (govNonce, deadline) = nextGov();
        sigs = govSigs(action, paramsHash, govNonce, deadline, signerKeys);
    }

    function govSigs(
        bytes32 action,
        bytes32 paramsHash,
        uint256 govNonce,
        uint256 deadline,
        uint256[] memory signerKeys
    ) internal view returns (bytes[] memory) {
        return signAll(govDigest(action, paramsHash, govNonce, deadline), signerKeys);
    }

    function nextGov() internal returns (uint256 govNonce, uint256 deadline) {
        govNonce = _nextGovNonce++;
        deadline = block.timestamp + 1 hours;
    }

    function twoTrustees() internal view returns (uint256[] memory) {
        return keys(trustee1Key, trustee2Key);
    }

    function mandate(uint256 cap, uint256 hardCeiling, uint256 dailyBudget, uint256 perBeneficiaryCap)
        internal
        view
        returns (IAmanahVault.Mandate memory)
    {
        return IAmanahVault.Mandate({
            cap: cap * USDC,
            hardCeiling: hardCeiling * USDC,
            dailyBudget: dailyBudget * USDC,
            perBeneficiaryCap: perBeneficiaryCap * USDC,
            expiry: uint64(block.timestamp + 365 days),
            purposeHash: keccak256("demo programme"),
            active: true
        });
    }

    // Signing

    function signDigest(uint256 key, bytes32 digest) internal pure returns (bytes memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(key, digest);
        return abi.encodePacked(r, s, v);
    }

    function signAll(bytes32 digest, uint256[] memory signerKeys) internal pure returns (bytes[] memory sigs) {
        sigs = new bytes[](signerKeys.length);
        for (uint256 i = 0; i < signerKeys.length; ++i) {
            sigs[i] = signDigest(signerKeys[i], digest);
        }
    }

    function keys(uint256 a) internal pure returns (uint256[] memory k) {
        k = new uint256[](1);
        k[0] = a;
    }

    function keys(uint256 a, uint256 b) internal pure returns (uint256[] memory k) {
        k = new uint256[](2);
        (k[0], k[1]) = (a, b);
    }

    function keys(uint256 a, uint256 b, uint256 c) internal pure returns (uint256[] memory k) {
        k = new uint256[](3);
        (k[0], k[1], k[2]) = (a, b, c);
    }

    function keys(uint256 a, uint256 b, uint256 c, uint256 d) internal pure returns (uint256[] memory k) {
        k = new uint256[](4);
        (k[0], k[1], k[2], k[3]) = (a, b, c, d);
    }

    function keys(uint256 a, uint256 b, uint256 c, uint256 d, uint256 e) internal pure returns (uint256[] memory k) {
        k = new uint256[](5);
        (k[0], k[1], k[2], k[3], k[4]) = (a, b, c, d, e);
    }
}
