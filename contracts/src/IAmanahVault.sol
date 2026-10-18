// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IAmanahVault
/// @notice External interface of AmanahVault, as fixed in IMPLEMENTATION_PLAN.md section 3.2.
/// Lanes B, C and D build against this file and shared/abi/AmanahVault.json. Change it only
/// with a note in docs/decisions.md.
interface IAmanahVault {
    enum Role {
        NONE,
        PLANNER,
        AUDITOR,
        SENTINEL,
        TRUSTEE,
        GUARDIAN,
        POSTURE_ORACLE
    }

    enum Verdict {
        NONE,
        APPROVE,
        REJECT,
        ESCALATE
    }

    struct Signer {
        Role role;
        bytes32 lineage;
        bytes32 evidenceView;
        bool active;
    }

    struct Payout {
        bytes32 proposalId;
        bytes32 programmeId;
        address beneficiary;
        uint256 amount;
        bytes32 evidenceHash;
        uint256 nonce;
        uint256 deadline;
    }

    struct Mandate {
        uint256 cap;
        uint256 hardCeiling;
        uint256 dailyBudget;
        uint256 perBeneficiaryCap;
        uint64 expiry;
        bytes32 purposeHash;
        bool active;
    }

    struct Beneficiary {
        bytes32 idHash;
        uint64 activeFrom;
        bool active;
    }

    struct Decision {
        bytes32 proposalId;
        Verdict verdict;
        address signer;
        uint64 blockNumber;
    }

    event PayoutExecuted(
        bytes32 indexed proposalId,
        bytes32 indexed programmeId,
        address indexed beneficiary,
        uint256 amount,
        uint8 tier,
        address[] signers,
        bool override_
    );
    event DecisionAnchored(
        bytes32 indexed anchorId, bytes32 indexed proposalId, uint8 verdict, address signer, bytes32 evidenceHash
    );
    event ReportAnchored(bytes32 reportHash, address oracle);
    event PostureRaised(uint8 level, bytes32 reportHash);
    event PostureLowered(uint8 level);
    event SignerRegistered(address key, uint8 role, bytes32 lineage, bytes32 evidenceView);
    event SignerActiveSet(address key, bool active);
    event MandateSet(bytes32 indexed programmeId, Mandate m);
    event BeneficiaryAdded(bytes32 indexed programmeId, address wallet, bytes32 idHash, uint64 activeFrom);
    event BeneficiaryCancelled(bytes32 indexed programmeId, address wallet, address by);

    error Expired();
    error NonceUsed();
    error GovNonceUsed();
    error UnknownSigner();
    error InactiveSigner();
    error DuplicateSigner();
    error QuorumIncomplete();
    error SameLineage();
    error TrusteeRequired();
    error NotTrustee();
    error NotGuardian();
    error NotPostureOracle();
    error NotAllowlisted();
    error CoolingOff();
    error MandateInactive();
    error AboveHardCeiling();
    error DailyBudgetExceeded();
    error BeneficiaryCapExceeded();
    error PostureCanOnlyRise();
    error PostureCanOnlyFall();
    error NoSuchRefusal();
    error NotInCoolingOff();

    // Payouts

    /// @notice Pays `p.amount` USDC to `p.beneficiary` when the signatures form the quorum `tierOf(p)` demands.
    function execute(Payout calldata p, bytes[] calldata sigs) external;

    /// @notice Pays despite an anchored auditor or sentinel refusal, with the planner and two trustees.
    function executeOverride(Payout calldata p, bytes32 refusalAnchor, bytes[] calldata sigs) external;

    /// @notice 1 routine, 2 elevated. Reverts on hard limits: mandate, hard ceiling, daily budget, beneficiary cap.
    function tierOf(Payout calldata p) external view returns (uint8);

    /// @notice The EIP-712 digest every payout signature is made over.
    function hashPayout(Payout calldata p) external view returns (bytes32);

    // Anchoring and posture

    /// @notice Records a verdict on-chain. Caller must be an active PLANNER, AUDITOR or SENTINEL.
    function anchorDecision(bytes32 proposalId, Verdict verdict, bytes32 evidenceHash)
        external
        returns (bytes32 anchorId);

    /// @notice Records a red-team report hash. POSTURE_ORACLE only.
    function anchorReport(bytes32 reportHash) external;

    /// @notice Raises the security posture. POSTURE_ORACLE only, and only upwards.
    function raisePosture(uint8 level, bytes32 reportHash) external;

    function posture() external view returns (uint8);

    // Governance: two distinct TRUSTEE signatures over Governance(action, paramsHash, govNonce, deadline)

    function lowerPosture(uint8 level, uint256 govNonce, uint256 deadline, bytes[] calldata sigs) external;

    function registerSigner(
        address key,
        Role role,
        bytes32 lineage,
        bytes32 evidenceView,
        uint256 govNonce,
        uint256 deadline,
        bytes[] calldata sigs
    ) external;

    function setSignerActive(address key, bool active, uint256 govNonce, uint256 deadline, bytes[] calldata sigs)
        external;

    function setMandate(
        bytes32 programmeId,
        Mandate calldata m,
        uint256 govNonce,
        uint256 deadline,
        bytes[] calldata sigs
    ) external;

    function addBeneficiary(
        bytes32 programmeId,
        address wallet,
        bytes32 idHash,
        uint256 govNonce,
        uint256 deadline,
        bytes[] calldata sigs
    ) external;

    function unpause(uint256 govNonce, uint256 deadline, bytes[] calldata sigs) external;

    // Single-key actions

    /// @notice Any TRUSTEE or GUARDIAN, only while the beneficiary is still in cooling-off.
    function cancelBeneficiary(bytes32 programmeId, address wallet) external;

    /// @notice GUARDIAN only.
    function pause() external;

    // Views

    function signers(address key) external view returns (Signer memory);

    function mandates(bytes32 programmeId) external view returns (Mandate memory);

    function beneficiaries(bytes32 programmeId, address wallet) external view returns (Beneficiary memory);

    function decisions(bytes32 anchorId) external view returns (Decision memory);

    function spentToday(bytes32 programmeId) external view returns (uint256);
}
