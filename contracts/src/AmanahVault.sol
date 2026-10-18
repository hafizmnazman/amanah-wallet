// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

import {IAmanahVault} from "./IAmanahVault.sol";

/// @title AmanahVault
/// @notice Holds programme funds in USDC and pays a beneficiary only when a planner, an auditor of a
/// different lineage and a sentinel have signed the payout, plus a trustee when the risk tier demands it.
/// Its rules change only with signatures from two trustees. There is no admin role, and the deployer
/// holds no role after construction.
contract AmanahVault is IAmanahVault, EIP712, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    bytes32 public constant PAYOUT_TYPEHASH = keccak256(
        "Payout(bytes32 proposalId,bytes32 programmeId,address beneficiary,uint256 amount,bytes32 evidenceHash,uint256 nonce,uint256 deadline)"
    );
    bytes32 public constant GOVERNANCE_TYPEHASH =
        keccak256("Governance(bytes32 action,bytes32 paramsHash,uint256 govNonce,uint256 deadline)");

    bytes32 public constant ACTION_LOWER_POSTURE = keccak256("lowerPosture");
    bytes32 public constant ACTION_REGISTER_SIGNER = keccak256("registerSigner");
    bytes32 public constant ACTION_SET_SIGNER_ACTIVE = keccak256("setSignerActive");
    bytes32 public constant ACTION_SET_MANDATE = keccak256("setMandate");
    bytes32 public constant ACTION_ADD_BENEFICIARY = keccak256("addBeneficiary");
    bytes32 public constant ACTION_UNPAUSE = keccak256("unpause");

    /// @notice Lineage and evidence view of the trustees and the guardian registered at construction.
    bytes32 public constant HUMAN = keccak256("human");

    /// @notice Share of a programme's daily budget that may move without a trustee.
    uint256 public constant ROUTINE_SHARE_BPS = 8000;
    /// @notice Window for the per-beneficiary cap.
    uint256 public constant PERIOD = 30 days;

    uint8 public constant TIER_ROUTINE = 1;
    uint8 public constant TIER_ELEVATED = 2;
    /// @notice Tier reported in PayoutExecuted by executeOverride. tierOf never returns it.
    uint8 public constant TIER_OVERRIDE = 3;

    error ZeroAddress();
    error InvalidRole();
    error InvalidVerdict();
    error NotChecker();
    error TooFewTrustees();

    /// @dev Spend within one window: a day for the daily budget, a PERIOD for the beneficiary cap.
    struct Spend {
        uint256 window;
        uint256 amount;
    }

    /// @dev Signature count per role in one payout quorum.
    struct Quorum {
        uint256 planners;
        uint256 auditors;
        uint256 sentinels;
        uint256 trustees;
        address planner;
        address auditor;
    }

    IERC20 public immutable usdc;
    uint64 public immutable coolingOff;

    uint8 private _posture;
    /// @notice Hash of the latest red-team report anchored by the posture oracle.
    bytes32 public lastReportHash;
    /// @notice Timestamp of the latest posture change.
    uint64 public postureChangedAt;
    /// @notice Active TRUSTEE keys. Governance refuses to drop this below two.
    uint256 public activeTrustees;

    mapping(address key => Signer) private _signers;
    mapping(bytes32 programmeId => Mandate) private _mandates;
    mapping(bytes32 programmeId => mapping(address wallet => Beneficiary)) private _beneficiaries;
    mapping(bytes32 anchorId => Decision) private _decisions;
    mapping(bytes32 programmeId => Spend) private _daySpend;
    mapping(bytes32 programmeId => mapping(address wallet => Spend)) private _periodSpend;

    mapping(uint256 nonce => bool) public nonceUsed;
    mapping(uint256 govNonce => bool) public govNonceUsed;
    /// @notice Refusal anchors already cited by an override. Each refusal justifies one override.
    mapping(bytes32 anchorId => bool) public refusalUsed;

    constructor(address usdc_, address[3] memory trustees, address guardian, uint64 coolingOff_)
        EIP712("AmanahVault", "1")
    {
        if (usdc_ == address(0)) revert ZeroAddress();
        usdc = IERC20(usdc_);
        coolingOff = coolingOff_;
        for (uint256 i = 0; i < trustees.length; ++i) {
            _register(trustees[i], Role.TRUSTEE, HUMAN, HUMAN);
        }
        _register(guardian, Role.GUARDIAN, HUMAN, HUMAN);
    }

    // Payouts

    /// @inheritdoc IAmanahVault
    function execute(Payout calldata p, bytes[] calldata sigs) external whenNotPaused nonReentrant {
        _checkPayout(p);
        uint8 tier = tierOf(p);
        address[] memory keys = _recoverSigners(hashPayout(p), sigs);
        Quorum memory q = _countQuorum(keys);
        if (q.planners != 1 || q.auditors != 1 || q.sentinels != 1) revert QuorumIncomplete();
        if (_signers[q.planner].lineage == _signers[q.auditor].lineage) revert SameLineage();
        if (tier == TIER_ELEVATED && q.trustees == 0) revert TrusteeRequired();
        _pay(p, tier, keys, false);
    }

    /// @inheritdoc IAmanahVault
    /// @dev The refusal must be an anchored REJECT or ESCALATE for the same proposal, by a key registered
    /// as AUDITOR or SENTINEL, not cited before. Hard limits still apply; the cap and the 80% line do not.
    function executeOverride(Payout calldata p, bytes32 refusalAnchor, bytes[] calldata sigs)
        external
        whenNotPaused
        nonReentrant
    {
        _checkPayout(p);
        Decision storage d = _decisions[refusalAnchor];
        Role refuser = _signers[d.signer].role;
        if (
            d.proposalId != p.proposalId || (d.verdict != Verdict.REJECT && d.verdict != Verdict.ESCALATE)
                || (refuser != Role.AUDITOR && refuser != Role.SENTINEL) || refusalUsed[refusalAnchor]
        ) revert NoSuchRefusal();
        tierOf(p);
        address[] memory keys = _recoverSigners(hashPayout(p), sigs);
        Quorum memory q = _countQuorum(keys);
        if (q.planners != 1) revert QuorumIncomplete();
        if (q.trustees < 2) revert TrusteeRequired();
        refusalUsed[refusalAnchor] = true;
        _pay(p, TIER_OVERRIDE, keys, true);
    }

    /// @inheritdoc IAmanahVault
    function tierOf(Payout calldata p) public view returns (uint8) {
        Mandate storage m = _mandates[p.programmeId];
        if (!m.active || block.timestamp > m.expiry) revert MandateInactive();
        if (p.amount > m.hardCeiling) revert AboveHardCeiling();
        uint256 dayTotal = spentToday(p.programmeId) + p.amount;
        if (dayTotal > m.dailyBudget) revert DailyBudgetExceeded();
        if (spentThisPeriod(p.programmeId, p.beneficiary) + p.amount > m.perBeneficiaryCap) {
            revert BeneficiaryCapExceeded();
        }
        if (_posture > 0 || p.amount > m.cap || dayTotal * 10_000 > m.dailyBudget * ROUTINE_SHARE_BPS) {
            return TIER_ELEVATED;
        }
        return TIER_ROUTINE;
    }

    /// @inheritdoc IAmanahVault
    function hashPayout(Payout calldata p) public view returns (bytes32) {
        return _hashTypedDataV4(
            keccak256(
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
            )
        );
    }

    /// @notice The EIP-712 digest trustees sign for a governance call.
    function hashGovernance(bytes32 action, bytes32 paramsHash, uint256 govNonce, uint256 deadline)
        public
        view
        returns (bytes32)
    {
        return _hashTypedDataV4(keccak256(abi.encode(GOVERNANCE_TYPEHASH, action, paramsHash, govNonce, deadline)));
    }

    // Anchoring and posture

    /// @inheritdoc IAmanahVault
    function anchorDecision(bytes32 proposalId, Verdict verdict, bytes32 evidenceHash)
        external
        returns (bytes32 anchorId)
    {
        Signer storage s = _signers[msg.sender];
        if (!s.active || (s.role != Role.PLANNER && s.role != Role.AUDITOR && s.role != Role.SENTINEL)) {
            revert NotChecker();
        }
        if (verdict == Verdict.NONE) revert InvalidVerdict();
        anchorId = keccak256(abi.encode(proposalId, verdict, evidenceHash, msg.sender, block.number));
        _decisions[anchorId] = Decision(proposalId, verdict, msg.sender, uint64(block.number));
        emit DecisionAnchored(anchorId, proposalId, uint8(verdict), msg.sender, evidenceHash);
    }

    /// @inheritdoc IAmanahVault
    function anchorReport(bytes32 reportHash) external {
        _requirePostureOracle();
        lastReportHash = reportHash;
        emit ReportAnchored(reportHash, msg.sender);
    }

    /// @inheritdoc IAmanahVault
    function raisePosture(uint8 level, bytes32 reportHash) external {
        _requirePostureOracle();
        if (level <= _posture) revert PostureCanOnlyRise();
        _posture = level;
        lastReportHash = reportHash;
        postureChangedAt = uint64(block.timestamp);
        emit PostureRaised(level, reportHash);
    }

    /// @inheritdoc IAmanahVault
    function posture() external view returns (uint8) {
        return _posture;
    }

    // Governance

    /// @inheritdoc IAmanahVault
    function lowerPosture(uint8 level, uint256 govNonce, uint256 deadline, bytes[] calldata sigs) external {
        _requireTwoTrustees(ACTION_LOWER_POSTURE, keccak256(abi.encode(level)), govNonce, deadline, sigs);
        if (level >= _posture) revert PostureCanOnlyFall();
        _posture = level;
        postureChangedAt = uint64(block.timestamp);
        emit PostureLowered(level);
    }

    /// @inheritdoc IAmanahVault
    /// @dev A key is registered once. To rotate a key, register the new one and deactivate the old one.
    function registerSigner(
        address key,
        Role role,
        bytes32 lineage,
        bytes32 evidenceView,
        uint256 govNonce,
        uint256 deadline,
        bytes[] calldata sigs
    ) external {
        _requireTwoTrustees(
            ACTION_REGISTER_SIGNER, keccak256(abi.encode(key, role, lineage, evidenceView)), govNonce, deadline, sigs
        );
        _register(key, role, lineage, evidenceView);
    }

    /// @inheritdoc IAmanahVault
    function setSignerActive(address key, bool active, uint256 govNonce, uint256 deadline, bytes[] calldata sigs)
        external
    {
        _requireTwoTrustees(ACTION_SET_SIGNER_ACTIVE, keccak256(abi.encode(key, active)), govNonce, deadline, sigs);
        Signer storage s = _signers[key];
        if (s.role == Role.NONE) revert UnknownSigner();
        if (s.role == Role.TRUSTEE && s.active != active) {
            if (!active && activeTrustees <= 2) revert TooFewTrustees();
            activeTrustees = active ? activeTrustees + 1 : activeTrustees - 1;
        }
        s.active = active;
        emit SignerActiveSet(key, active);
    }

    /// @inheritdoc IAmanahVault
    function setMandate(
        bytes32 programmeId,
        Mandate calldata m,
        uint256 govNonce,
        uint256 deadline,
        bytes[] calldata sigs
    ) external {
        _requireTwoTrustees(ACTION_SET_MANDATE, keccak256(abi.encode(programmeId, m)), govNonce, deadline, sigs);
        if (m.cap > m.hardCeiling) revert AboveHardCeiling();
        _mandates[programmeId] = m;
        emit MandateSet(programmeId, m);
    }

    /// @inheritdoc IAmanahVault
    /// @dev Starts the cooling-off period. Adding a wallet again restarts it.
    function addBeneficiary(
        bytes32 programmeId,
        address wallet,
        bytes32 idHash,
        uint256 govNonce,
        uint256 deadline,
        bytes[] calldata sigs
    ) external {
        _requireTwoTrustees(
            ACTION_ADD_BENEFICIARY, keccak256(abi.encode(programmeId, wallet, idHash)), govNonce, deadline, sigs
        );
        if (wallet == address(0)) revert ZeroAddress();
        uint64 activeFrom = uint64(block.timestamp) + coolingOff;
        _beneficiaries[programmeId][wallet] = Beneficiary(idHash, activeFrom, true);
        emit BeneficiaryAdded(programmeId, wallet, idHash, activeFrom);
    }

    /// @inheritdoc IAmanahVault
    function unpause(uint256 govNonce, uint256 deadline, bytes[] calldata sigs) external {
        _requireTwoTrustees(ACTION_UNPAUSE, keccak256(abi.encode()), govNonce, deadline, sigs);
        _unpause();
    }

    // Single-key actions

    /// @inheritdoc IAmanahVault
    function cancelBeneficiary(bytes32 programmeId, address wallet) external {
        Signer storage s = _signers[msg.sender];
        if (!s.active || (s.role != Role.TRUSTEE && s.role != Role.GUARDIAN)) revert NotTrustee();
        Beneficiary storage b = _beneficiaries[programmeId][wallet];
        if (!b.active) revert NotAllowlisted();
        if (block.timestamp >= b.activeFrom) revert NotInCoolingOff();
        b.active = false;
        emit BeneficiaryCancelled(programmeId, wallet, msg.sender);
    }

    /// @inheritdoc IAmanahVault
    function pause() external {
        Signer storage s = _signers[msg.sender];
        if (s.role != Role.GUARDIAN || !s.active) revert NotGuardian();
        _pause();
    }

    // Views

    /// @inheritdoc IAmanahVault
    function signers(address key) external view returns (Signer memory) {
        return _signers[key];
    }

    /// @inheritdoc IAmanahVault
    function mandates(bytes32 programmeId) external view returns (Mandate memory) {
        return _mandates[programmeId];
    }

    /// @inheritdoc IAmanahVault
    function beneficiaries(bytes32 programmeId, address wallet) external view returns (Beneficiary memory) {
        return _beneficiaries[programmeId][wallet];
    }

    /// @inheritdoc IAmanahVault
    function decisions(bytes32 anchorId) external view returns (Decision memory) {
        return _decisions[anchorId];
    }

    /// @inheritdoc IAmanahVault
    function spentToday(bytes32 programmeId) public view returns (uint256) {
        return _spentIn(_daySpend[programmeId], block.timestamp / 1 days);
    }

    /// @notice What a beneficiary has received from a programme in the current PERIOD.
    function spentThisPeriod(bytes32 programmeId, address wallet) public view returns (uint256) {
        return _spentIn(_periodSpend[programmeId][wallet], block.timestamp / PERIOD);
    }

    // Internals

    function _checkPayout(Payout calldata p) private view {
        if (block.timestamp > p.deadline) revert Expired();
        if (nonceUsed[p.nonce]) revert NonceUsed();
        Beneficiary storage b = _beneficiaries[p.programmeId][p.beneficiary];
        if (!b.active) revert NotAllowlisted();
        if (block.timestamp < b.activeFrom) revert CoolingOff();
    }

    function _pay(Payout calldata p, uint8 tier, address[] memory keys, bool isOverride) private {
        nonceUsed[p.nonce] = true;
        _addSpend(_daySpend[p.programmeId], block.timestamp / 1 days, p.amount);
        _addSpend(_periodSpend[p.programmeId][p.beneficiary], block.timestamp / PERIOD, p.amount);
        usdc.safeTransfer(p.beneficiary, p.amount);
        emit PayoutExecuted(p.proposalId, p.programmeId, p.beneficiary, p.amount, tier, keys, isOverride);
    }

    /// @dev Recovers every signature over `digest`. Each key must be registered, active and appear once.
    function _recoverSigners(bytes32 digest, bytes[] calldata sigs) private view returns (address[] memory keys) {
        keys = new address[](sigs.length);
        for (uint256 i = 0; i < sigs.length; ++i) {
            address key = ECDSA.recover(digest, sigs[i]);
            Signer storage s = _signers[key];
            if (s.role == Role.NONE) revert UnknownSigner();
            if (!s.active) revert InactiveSigner();
            for (uint256 j = 0; j < i; ++j) {
                if (keys[j] == key) revert DuplicateSigner();
            }
            keys[i] = key;
        }
    }

    /// @dev A payout quorum may hold planner, auditor, sentinel and trustee keys only.
    function _countQuorum(address[] memory keys) private view returns (Quorum memory q) {
        for (uint256 i = 0; i < keys.length; ++i) {
            Role role = _signers[keys[i]].role;
            if (role == Role.PLANNER) {
                ++q.planners;
                q.planner = keys[i];
            } else if (role == Role.AUDITOR) {
                ++q.auditors;
                q.auditor = keys[i];
            } else if (role == Role.SENTINEL) {
                ++q.sentinels;
            } else if (role == Role.TRUSTEE) {
                ++q.trustees;
            } else {
                revert QuorumIncomplete();
            }
        }
    }

    function _requireTwoTrustees(
        bytes32 action,
        bytes32 paramsHash,
        uint256 govNonce,
        uint256 deadline,
        bytes[] calldata sigs
    ) private {
        if (govNonceUsed[govNonce]) revert GovNonceUsed();
        if (block.timestamp > deadline) revert Expired();
        bytes32 digest = hashGovernance(action, paramsHash, govNonce, deadline);
        address[] memory seen = new address[](sigs.length);
        for (uint256 i = 0; i < sigs.length; ++i) {
            address key = ECDSA.recover(digest, sigs[i]);
            Signer storage s = _signers[key];
            if (s.role != Role.TRUSTEE) revert NotTrustee();
            if (!s.active) revert InactiveSigner();
            for (uint256 j = 0; j < i; ++j) {
                if (seen[j] == key) revert DuplicateSigner();
            }
            seen[i] = key;
        }
        if (sigs.length < 2) revert QuorumIncomplete();
        govNonceUsed[govNonce] = true;
    }

    function _register(address key, Role role, bytes32 lineage, bytes32 evidenceView) private {
        if (key == address(0)) revert ZeroAddress();
        if (role == Role.NONE) revert InvalidRole();
        if (_signers[key].role != Role.NONE) revert DuplicateSigner();
        _signers[key] = Signer(role, lineage, evidenceView, true);
        if (role == Role.TRUSTEE) ++activeTrustees;
        emit SignerRegistered(key, uint8(role), lineage, evidenceView);
    }

    function _requirePostureOracle() private view {
        Signer storage s = _signers[msg.sender];
        if (s.role != Role.POSTURE_ORACLE || !s.active) revert NotPostureOracle();
    }

    function _addSpend(Spend storage s, uint256 window, uint256 amount) private {
        if (s.window != window) {
            s.window = window;
            s.amount = amount;
        } else {
            s.amount += amount;
        }
    }

    function _spentIn(Spend storage s, uint256 window) private view returns (uint256) {
        return s.window == window ? s.amount : 0;
    }
}
