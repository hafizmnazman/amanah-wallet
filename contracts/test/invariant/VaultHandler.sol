// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {CommonBase} from "forge-std/Base.sol";
import {StdCheats} from "forge-std/StdCheats.sol";
import {StdUtils} from "forge-std/StdUtils.sol";

import {AmanahLabels as L} from "../../src/AmanahLabels.sol";
import {AmanahVault} from "../../src/AmanahVault.sol";
import {IAmanahVault} from "../../src/IAmanahVault.sol";
import {MockUSDC} from "../../src/mocks/MockUSDC.sol";

/// @dev Drives random sequences of payouts, overrides, anchors, governance calls with valid and invalid
/// signer sets, pause, posture changes and time. It keeps its own record of the registry, the allowlist,
/// the mandates and every amount paid, and counts each success the rules should have refused. The
/// invariants in Invariant.t.sol assert that every counter stays at zero.
contract VaultHandler is CommonBase, StdCheats, StdUtils {
    uint256 internal constant USDC = 1e6;
    uint256 public constant INITIAL_BALANCE = 10_000_000 * USDC;
    uint64 internal constant COOLING_OFF = 1 hours;

    // Key indexes into `pk` and `who`
    uint256 internal constant PLANNER = 0;
    uint256 internal constant AUDITOR = 1;
    uint256 internal constant CLAUDE_AUDITOR = 2;
    uint256 internal constant SENTINEL = 3;
    uint256 internal constant TRUSTEE1 = 4;
    uint256 internal constant TRUSTEE2 = 5;
    uint256 internal constant TRUSTEE3 = 6;
    uint256 internal constant GUARDIAN = 7;
    uint256 internal constant ORACLE = 8;
    uint256 internal constant ATTACKER = 9;
    uint256 internal constant EXTRA1 = 10;
    uint256 internal constant EXTRA2 = 11;
    uint256 internal constant KEY_COUNT = 12;

    bytes32 internal constant ZKT = keccak256("ZKT-IPOH-FAKIR-M");
    bytes32 internal constant REL = keccak256("REL-PERAK-FLOOD");

    struct GhostSigner {
        IAmanahVault.Role role;
        bytes32 lineage;
        bool active;
    }

    struct GhostAnchor {
        bytes32 proposalId;
        IAmanahVault.Verdict verdict;
        address signer;
    }

    struct Gov {
        uint256 nonce;
        uint256 deadline;
        uint256[] idx;
        bytes[] sigs;
    }

    struct Sent {
        IAmanahVault.Payout p;
        uint256[] idx;
        bool isOverride;
        bytes32 anchorId;
    }

    AmanahVault public immutable vault;
    MockUSDC public immutable usdc;

    uint256[KEY_COUNT] internal pk;
    address[KEY_COUNT] internal who;
    bytes32[2] internal programmes = [ZKT, REL];
    address[8] internal wallets;

    // The handler's own record of the vault's rules
    mapping(address key => GhostSigner) internal ghostSigner;
    mapping(bytes32 programmeId => IAmanahVault.Mandate) internal ghostMandate;
    mapping(bytes32 programmeId => mapping(address wallet => uint64)) internal ghostActiveFrom;
    mapping(bytes32 anchorId => GhostAnchor) internal ghostAnchor;
    mapping(bytes32 anchorId => bool) internal ghostRefusalUsed;
    uint8 public ghostPosture;
    bool public ghostPaused;

    // The handler's own record of what moved
    mapping(bytes32 programmeId => mapping(uint256 day => uint256)) internal daySpend;
    mapping(bytes32 programmeId => mapping(uint256 day => uint256)) internal machineDaySpend;
    mapping(bytes32 programmeId => mapping(address wallet => mapping(uint256 period => uint256))) internal periodSpend;
    mapping(uint256 nonce => uint256) internal nonceSuccesses;
    mapping(uint256 govNonce => uint256) internal govNonceSuccesses;

    uint256 internal nextNonce = 1;
    uint256 internal nextGovNonce = 1;
    uint256[] internal usedGovNonces;
    bytes32[] internal anchors;
    Sent[] internal sent;

    // Activity, to show the invariants were not checked against an idle vault
    uint256 public paidOut;
    uint256 public payouts;
    uint256 public overrides;
    uint256 public governanceSuccesses;

    // Each counts successes the rules should have refused; every invariant asserts one of them is zero
    uint256 public badRecipient;
    uint256 public overBudget;
    uint256 public outsideMandate;
    uint256 public overMachineLine;
    uint256 public machineElevated;
    uint256 public overBeneficiaryCap;
    uint256 public sameLineage;
    uint256 public illegalPosture;
    uint256 public replays;
    uint256 public badOverride;
    uint256 public badAuthority;
    uint256 public paidWhilePaused;

    constructor() {
        string[KEY_COUNT] memory names = [
            "planner",
            "auditor",
            "claude-auditor",
            "sentinel",
            "trustee1",
            "trustee2",
            "trustee3",
            "guardian",
            "posture-oracle",
            "attacker",
            "extra1",
            "extra2"
        ];
        for (uint256 i = 0; i < KEY_COUNT; ++i) {
            (who[i], pk[i]) = makeAddrAndKey(names[i]);
        }
        for (uint256 i = 0; i < wallets.length; ++i) {
            wallets[i] = makeAddr(string.concat("wallet-", vm.toString(i)));
        }

        usdc = new MockUSDC();
        vault =
            new AmanahVault(address(usdc), [who[TRUSTEE1], who[TRUSTEE2], who[TRUSTEE3]], who[GUARDIAN], COOLING_OFF);
        for (uint256 i = TRUSTEE1; i <= TRUSTEE3; ++i) {
            ghostSigner[who[i]] = GhostSigner(IAmanahVault.Role.TRUSTEE, L.LINEAGE_HUMAN, true);
        }
        ghostSigner[who[GUARDIAN]] = GhostSigner(IAmanahVault.Role.GUARDIAN, L.LINEAGE_HUMAN, true);

        _setupRegister(PLANNER, IAmanahVault.Role.PLANNER, L.LINEAGE_CLAUDE);
        _setupRegister(AUDITOR, IAmanahVault.Role.AUDITOR, L.LINEAGE_QWEN);
        _setupRegister(CLAUDE_AUDITOR, IAmanahVault.Role.AUDITOR, L.LINEAGE_CLAUDE);
        _setupRegister(SENTINEL, IAmanahVault.Role.SENTINEL, L.LINEAGE_RULES);
        _setupRegister(ORACLE, IAmanahVault.Role.POSTURE_ORACLE, L.LINEAGE_GPT);

        // Plan section 10 numbers, with an expiry past any sequence's end
        _setupMandate(
            ZKT,
            IAmanahVault.Mandate(
                200 * USDC,
                1500 * USDC,
                2500 * USDC,
                400 * USDC,
                uint64(block.timestamp + 3650 days),
                keccak256("zakat"),
                true
            )
        );
        _setupMandate(
            REL,
            IAmanahVault.Mandate(
                300 * USDC,
                2000 * USDC,
                3000 * USDC,
                600 * USDC,
                uint64(block.timestamp + 3650 days),
                keccak256("relief"),
                true
            )
        );

        // Wallets 0 to 4 for zakat, 2 to 6 for relief, 7 for neither
        for (uint256 i = 0; i < 7; ++i) {
            if (i <= 4) _setupBeneficiary(ZKT, wallets[i]);
            if (i >= 2) _setupBeneficiary(REL, wallets[i]);
        }
        vm.warp(block.timestamp + COOLING_OFF);
        usdc.mint(address(vault), INITIAL_BALANCE);
    }

    // Payouts

    function execute(uint256 programmeSeed, uint256 walletSeed, uint256 amount, uint256 seed) external {
        IAmanahVault.Payout memory p = _payout(programmeSeed, walletSeed, amount, seed);
        uint256[] memory idx = _payoutShape(seed);
        try vault.execute(p, _payoutSigs(p, idx)) {
            _recordPayout(p, idx, false, bytes32(0));
        } catch {}
        _check();
    }

    /// @dev Pays up to six allowlisted wallets of one programme at the cap in one call, so runs reach the
    /// 80% line, the daily budget and the beneficiary caps. Half the batches carry a trustee signature.
    function executeBatch(uint256 programmeSeed, uint256 countSeed, uint256 seed) external {
        bytes32 pid = programmes[programmeSeed % 2];
        uint256 count = 1 + countSeed % 6;
        uint256[] memory idx =
            seed % 2 == 0 ? _idx(PLANNER, AUDITOR, SENTINEL, TRUSTEE1) : _idx(PLANNER, AUDITOR, SENTINEL);
        for (uint256 i = 0; i < count; ++i) {
            address wallet = wallets[(pid == ZKT ? 0 : 2) + (seed % 5 + i) % 5];
            IAmanahVault.Payout memory p = IAmanahVault.Payout({
                proposalId: keccak256(abi.encode("proposal", (seed % 8 + i) % 8)),
                programmeId: pid,
                beneficiary: wallet,
                amount: ghostMandate[pid].cap,
                evidenceHash: keccak256(abi.encode(seed, i)),
                nonce: nextNonce++,
                deadline: block.timestamp + 1 hours
            });
            try vault.execute(p, _payoutSigs(p, idx)) {
                _recordPayout(p, idx, false, bytes32(0));
            } catch {}
        }
        _check();
    }

    function executeOverride(uint256 programmeSeed, uint256 walletSeed, uint256 amount, uint256 seed) external {
        IAmanahVault.Payout memory p = _payout(programmeSeed, walletSeed, amount, seed);
        bytes32 anchorId = keccak256(abi.encode("no such anchor", seed));
        if (anchors.length > 0 && seed % 5 != 0) {
            anchorId = anchors[(seed >> 24) % anchors.length];
            p.proposalId = ghostAnchor[anchorId].proposalId;
        }
        uint256[] memory idx = _overrideShape(seed);
        try vault.executeOverride(p, anchorId, _payoutSigs(p, idx)) {
            _recordPayout(p, idx, true, anchorId);
        } catch {}
        _check();
    }

    /// @dev Resubmits an earlier successful payout with the same signatures.
    function replay(uint256 seed) external {
        if (sent.length == 0) return;
        Sent memory s = sent[seed % sent.length];
        bytes[] memory sigs = _payoutSigs(s.p, s.idx);
        if (s.isOverride) {
            try vault.executeOverride(s.p, s.anchorId, sigs) {
                _recordPayout(s.p, s.idx, true, s.anchorId);
            } catch {}
        } else {
            try vault.execute(s.p, sigs) {
                _recordPayout(s.p, s.idx, false, bytes32(0));
            } catch {}
        }
        _check();
    }

    function anchor(uint256 actorSeed, uint256 verdictSeed, uint256 proposalSeed) external {
        uint256[6] memory actors = [AUDITOR, SENTINEL, AUDITOR, PLANNER, TRUSTEE1, ATTACKER];
        address actor = who[actors[actorSeed % actors.length]];
        IAmanahVault.Verdict verdict = IAmanahVault.Verdict(verdictSeed % 4);
        bytes32 proposalId = keccak256(abi.encode("proposal", proposalSeed % 8));
        vm.prank(actor);
        try vault.anchorDecision(proposalId, verdict, bytes32(proposalSeed)) returns (bytes32 anchorId) {
            GhostSigner memory g = ghostSigner[actor];
            bool checker = g.role == IAmanahVault.Role.PLANNER || g.role == IAmanahVault.Role.AUDITOR
                || g.role == IAmanahVault.Role.SENTINEL;
            if (!checker || !g.active || verdict == IAmanahVault.Verdict.NONE) ++badAuthority;
            ghostAnchor[anchorId] = GhostAnchor(proposalId, verdict, actor);
            anchors.push(anchorId);
        } catch {}
        _check();
    }

    // Governance, with valid and invalid signer sets and replayed nonces

    function setMandate(uint256 programmeSeed, uint256 capSeed, uint256 budgetSeed, uint256 seed) external {
        bytes32 pid = programmes[programmeSeed % 2];
        IAmanahVault.Mandate memory m = _mandateFrom(capSeed, budgetSeed, seed);
        Gov memory g = _gov(vault.ACTION_SET_MANDATE(), keccak256(abi.encode(pid, m)), seed);
        try vault.setMandate(pid, m, g.nonce, g.deadline, g.sigs) {
            _recordGovernance(g);
            if (m.cap > m.hardCeiling) ++badAuthority;
            ghostMandate[pid] = m;
        } catch {}
        _check();
    }

    function addBeneficiary(uint256 programmeSeed, uint256 walletSeed, uint256 seed) external {
        bytes32 pid = programmes[programmeSeed % 2];
        address wallet = wallets[walletSeed % wallets.length];
        Gov memory g = _gov(vault.ACTION_ADD_BENEFICIARY(), keccak256(abi.encode(pid, wallet, bytes32(seed))), seed);
        try vault.addBeneficiary(pid, wallet, bytes32(seed), g.nonce, g.deadline, g.sigs) {
            _recordGovernance(g);
            ghostActiveFrom[pid][wallet] = uint64(block.timestamp) + COOLING_OFF;
        } catch {}
        _check();
    }

    function setSignerActive(uint256 targetSeed, bool active, uint256 seed) external {
        address key = who[targetSeed % KEY_COUNT];
        active = active || seed % 3 != 0; // deactivate one call in three so payouts keep flowing
        Gov memory g = _gov(vault.ACTION_SET_SIGNER_ACTIVE(), keccak256(abi.encode(key, active)), seed);
        try vault.setSignerActive(key, active, g.nonce, g.deadline, g.sigs) {
            _recordGovernance(g);
            if (ghostSigner[key].role == IAmanahVault.Role.NONE) ++badAuthority;
            ghostSigner[key].active = active;
            if (_activeTrustees() < 2) ++badAuthority;
        } catch {}
        _check();
    }

    function registerSigner(uint256 keySeed, uint256 roleSeed, uint256 lineageSeed, uint256 seed) external {
        address key = who[keySeed % 2 == 0 ? EXTRA1 : EXTRA2];
        IAmanahVault.Role role = IAmanahVault.Role(roleSeed % 5);
        bytes32[4] memory lineages = [L.LINEAGE_CLAUDE, L.LINEAGE_QWEN, L.LINEAGE_GPT, L.LINEAGE_RULES];
        bytes32 lineage = lineages[lineageSeed % 4];
        Gov memory g =
            _gov(vault.ACTION_REGISTER_SIGNER(), keccak256(abi.encode(key, role, lineage, L.VIEW_NUMBERS)), seed);
        try vault.registerSigner(key, role, lineage, L.VIEW_NUMBERS, g.nonce, g.deadline, g.sigs) {
            _recordGovernance(g);
            if (role == IAmanahVault.Role.NONE || ghostSigner[key].role != IAmanahVault.Role.NONE) ++badAuthority;
            ghostSigner[key] = GhostSigner(role, lineage, true);
        } catch {}
        _check();
    }

    function lowerPosture(uint256 levelSeed, uint256 seed) external {
        uint8 level = uint8(bound(levelSeed, 0, 2));
        Gov memory g = _gov(vault.ACTION_LOWER_POSTURE(), keccak256(abi.encode(level)), seed);
        try vault.lowerPosture(level, g.nonce, g.deadline, g.sigs) {
            bool legitimate = _isTwoTrusteeSet(g.idx) && level < ghostPosture;
            _recordGovernance(g);
            if (legitimate) ghostPosture = level;
            else ++illegalPosture;
        } catch {}
        _check();
    }

    function unpause(uint256 seed) external {
        Gov memory g = _gov(vault.ACTION_UNPAUSE(), keccak256(abi.encode()), seed);
        try vault.unpause(g.nonce, g.deadline, g.sigs) {
            _recordGovernance(g);
            if (!ghostPaused) ++badAuthority;
            ghostPaused = false;
        } catch {}
        _check();
    }

    // Single-key actions

    function pause(uint256 actorSeed) external {
        // The guardian acts one call in sixteen, so the vault is not paused most of the time.
        address actor = actorSeed % 16 == 0
            ? who[GUARDIAN]
            : who[actorSeed % KEY_COUNT == GUARDIAN ? ATTACKER : actorSeed % KEY_COUNT];
        vm.prank(actor);
        try vault.pause() {
            GhostSigner memory g = ghostSigner[actor];
            if (g.role != IAmanahVault.Role.GUARDIAN || !g.active || ghostPaused) ++badAuthority;
            ghostPaused = true;
        } catch {}
        _check();
    }

    function raisePosture(uint256 levelSeed, uint256 actorSeed) external {
        address actor = who[actorSeed % 4 == 0 ? ORACLE : ATTACKER];
        uint8 level = uint8(bound(levelSeed, 0, 3));
        vm.prank(actor);
        try vault.raisePosture(level, bytes32(levelSeed)) {
            GhostSigner memory g = ghostSigner[actor];
            if (g.role != IAmanahVault.Role.POSTURE_ORACLE || !g.active || level <= ghostPosture) ++illegalPosture;
            else ghostPosture = level;
        } catch {}
        _check();
    }

    function cancelBeneficiary(uint256 programmeSeed, uint256 walletSeed, uint256 actorSeed) external {
        bytes32 pid = programmes[programmeSeed % 2];
        address wallet = wallets[walletSeed % wallets.length];
        uint256[4] memory actors = [TRUSTEE1, GUARDIAN, PLANNER, ATTACKER];
        address actor = who[actors[actorSeed % 4]];
        vm.prank(actor);
        try vault.cancelBeneficiary(pid, wallet) {
            GhostSigner memory g = ghostSigner[actor];
            bool allowed = g.active && (g.role == IAmanahVault.Role.TRUSTEE || g.role == IAmanahVault.Role.GUARDIAN);
            uint64 activeFrom = ghostActiveFrom[pid][wallet];
            if (!allowed || activeFrom == 0 || block.timestamp >= activeFrom) ++badAuthority;
            ghostActiveFrom[pid][wallet] = 0;
        } catch {}
        _check();
    }

    function warp(uint256 secondsSeed) external {
        vm.warp(block.timestamp + bound(secondsSeed, 1, 3 days));
        vm.roll(block.number + 1);
        _check();
    }

    // Building calls

    function _payout(uint256 programmeSeed, uint256 walletSeed, uint256 amount, uint256 seed)
        internal
        returns (IAmanahVault.Payout memory p)
    {
        bytes32 pid = programmes[programmeSeed % 2];
        IAmanahVault.Mandate memory m = ghostMandate[pid];
        // A third exactly at the cap, a quarter anywhere up to a fifth past the hard ceiling, the rest within the cap
        if (seed % 3 == 0) amount = m.cap;
        else if (seed % 4 == 0) amount = bound(amount, 0, m.hardCeiling + m.hardCeiling / 5);
        else amount = bound(amount, 1, m.cap);
        p = IAmanahVault.Payout({
            proposalId: keccak256(abi.encode("proposal", (seed >> 32) % 8)),
            programmeId: pid,
            beneficiary: _wallet(pid, walletSeed),
            amount: amount,
            evidenceHash: keccak256(abi.encode(seed)),
            nonce: nextNonce++,
            deadline: seed % 23 == 0 ? block.timestamp - 1 : block.timestamp + 1 hours
        });
    }

    /// @dev Three times in four a wallet allowlisted for the programme, otherwise any of the eight.
    function _wallet(bytes32 pid, uint256 walletSeed) internal view returns (address) {
        if (walletSeed % 4 == 0) return wallets[(walletSeed >> 8) % wallets.length];
        return wallets[(pid == ZKT ? 0 : 2) + (walletSeed >> 8) % 5];
    }

    /// @dev Ten shapes in sixteen are a valid quorum, four of them with trustees; the rest are broken on purpose.
    function _payoutShape(uint256 seed) internal pure returns (uint256[] memory) {
        uint256 s = (seed >> 8) % 16;
        bool alt = (seed >> 12) % 2 == 1;
        if (s <= 5) return _idx(PLANNER, AUDITOR, SENTINEL);
        if (s == 6) return _idx(PLANNER, AUDITOR, SENTINEL, TRUSTEE1);
        if (s == 7) return _idx(TRUSTEE3, SENTINEL, AUDITOR, PLANNER, TRUSTEE2);
        if (s == 8) return _idx(SENTINEL, AUDITOR, PLANNER, TRUSTEE3);
        if (s == 9) return _idx(PLANNER, AUDITOR, SENTINEL, TRUSTEE2);
        if (s == 10) return _idx(PLANNER, CLAUDE_AUDITOR, SENTINEL);
        if (s == 11) return _idx(PLANNER, CLAUDE_AUDITOR, SENTINEL, TRUSTEE1);
        if (s == 12) return _idx(PLANNER, AUDITOR, TRUSTEE1);
        if (s == 13) return alt ? _idx(PLANNER, AUDITOR, SENTINEL, GUARDIAN) : _idx(PLANNER, ATTACKER, SENTINEL);
        if (s == 14) return alt ? _idx(PLANNER, AUDITOR, SENTINEL, AUDITOR) : _idx(EXTRA1, AUDITOR, SENTINEL);
        return alt ? _idx(PLANNER, EXTRA2, SENTINEL, TRUSTEE2) : _idx(PLANNER, AUDITOR, CLAUDE_AUDITOR, SENTINEL);
    }

    function _overrideShape(uint256 seed) internal pure returns (uint256[] memory) {
        uint256 s = (seed >> 8) % 10;
        if (s == 0) return _idx(PLANNER, TRUSTEE1, TRUSTEE2);
        if (s == 1) return _idx(TRUSTEE3, PLANNER, TRUSTEE2);
        if (s == 2) return _idx(PLANNER, TRUSTEE1, TRUSTEE2, TRUSTEE3);
        if (s == 3) return _idx(PLANNER, TRUSTEE1, TRUSTEE3, SENTINEL);
        if (s == 4) return _idx(PLANNER, TRUSTEE1);
        if (s == 5) return _idx(TRUSTEE1, TRUSTEE2);
        if (s == 6) return _idx(PLANNER, TRUSTEE1, TRUSTEE1);
        if (s == 7) return _idx(PLANNER, TRUSTEE1, GUARDIAN);
        if (s == 8) return _idx(PLANNER, ATTACKER, TRUSTEE2);
        return _idx(EXTRA1, TRUSTEE1, TRUSTEE2);
    }

    /// @dev Half the time two or three distinct trustees; otherwise one, a repeat, a stranger or none.
    function _govShape(uint256 seed) internal pure returns (uint256[] memory) {
        uint256 s = (seed >> 16) % 10;
        if (s == 0 || s == 4) return _idx(TRUSTEE1, TRUSTEE2);
        if (s == 1) return _idx(TRUSTEE2, TRUSTEE3);
        if (s == 2) return _idx(TRUSTEE3, TRUSTEE1);
        if (s == 3) return _idx(TRUSTEE1, TRUSTEE2, TRUSTEE3);
        if (s == 5) return _idx(TRUSTEE1);
        if (s == 6) return _idx(TRUSTEE1, TRUSTEE1);
        if (s == 7) return _idx(TRUSTEE2, PLANNER);
        if (s == 8) return _idx(ATTACKER, TRUSTEE3);
        return new uint256[](0);
    }

    function _gov(bytes32 action, bytes32 paramsHash, uint256 seed) internal returns (Gov memory g) {
        // One call in ten replays a governance nonce that already executed
        g.nonce = seed % 10 == 0 && usedGovNonces.length > 0
            ? usedGovNonces[(seed >> 40) % usedGovNonces.length]
            : nextGovNonce++;
        g.deadline = seed % 19 == 0 ? block.timestamp - 1 : block.timestamp + 1 hours;
        g.idx = _govShape(seed);
        bytes32 digest = vault.hashGovernance(action, paramsHash, g.nonce, g.deadline);
        g.sigs = new bytes[](g.idx.length);
        for (uint256 i = 0; i < g.idx.length; ++i) {
            g.sigs[i] = _sign(pk[g.idx[i]], digest);
        }
    }

    function _mandateFrom(uint256 capSeed, uint256 budgetSeed, uint256 seed)
        internal
        view
        returns (IAmanahVault.Mandate memory m)
    {
        // Modulo rather than bound: the fuzzer favours small seeds, and these should still be realistic programmes.
        m.cap = (100 + capSeed % 400) * USDC;
        m.hardCeiling = seed % 9 == 0 ? m.cap - 1 : m.cap + ((capSeed >> 32) % 2000) * USDC;
        m.dailyBudget = (1000 + budgetSeed % 4000) * USDC;
        m.perBeneficiaryCap = m.cap + ((budgetSeed >> 32) % 1000) * USDC;
        m.expiry = uint64(block.timestamp + 365 days);
        m.purposeHash = keccak256(abi.encode(seed));
        m.active = seed % 11 != 0;
    }

    function _payoutSigs(IAmanahVault.Payout memory p, uint256[] memory idx)
        internal
        view
        returns (bytes[] memory sigs)
    {
        bytes32 digest = vault.hashPayout(p);
        sigs = new bytes[](idx.length);
        for (uint256 i = 0; i < idx.length; ++i) {
            sigs[i] = _sign(pk[idx[i]], digest);
        }
    }

    // Checking

    function _recordPayout(IAmanahVault.Payout memory p, uint256[] memory idx, bool isOverride, bytes32 anchorId)
        internal
    {
        IAmanahVault.Mandate memory m = ghostMandate[p.programmeId];
        uint256 day = block.timestamp / 1 days;
        ++payouts;
        paidOut += p.amount;
        if (++nonceSuccesses[p.nonce] > 1) ++replays;
        if (ghostPaused) ++paidWhilePaused;

        uint64 activeFrom = ghostActiveFrom[p.programmeId][p.beneficiary];
        if (activeFrom == 0 || block.timestamp < activeFrom) ++badRecipient;
        if (!m.active || block.timestamp > m.expiry || p.amount > m.hardCeiling) ++outsideMandate;
        if ((daySpend[p.programmeId][day] += p.amount) > m.dailyBudget) ++overBudget;
        uint256 period = block.timestamp / 30 days;
        if ((periodSpend[p.programmeId][p.beneficiary][period] += p.amount) > m.perBeneficiaryCap) {
            ++overBeneficiaryCap;
        }

        (uint256 planners, uint256 trustees, bytes32 plannerLineage, bytes32 auditorLineage) = _scan(idx);
        if (trustees == 0) {
            uint256 machine = (machineDaySpend[p.programmeId][day] += p.amount);
            if (machine * 10_000 > m.dailyBudget * 8000) ++overMachineLine;
            if (ghostPosture > 0 || p.amount > m.cap) ++machineElevated;
        }
        if (isOverride) {
            ++overrides;
            if (!_validRefusal(anchorId, p.proposalId) || trustees < 2 || planners != 1) ++badOverride;
            ghostRefusalUsed[anchorId] = true;
        } else if (plannerLineage == auditorLineage) {
            ++sameLineage;
        }
        sent.push(Sent(p, idx, isOverride, anchorId));
    }

    function _recordGovernance(Gov memory g) internal {
        ++governanceSuccesses;
        if (!_isTwoTrusteeSet(g.idx)) ++badAuthority;
        if (++govNonceSuccesses[g.nonce] > 1) ++replays;
        else usedGovNonces.push(g.nonce);
    }

    /// @dev Called after every action: posture and pause may only have moved by a recorded legitimate step.
    function _check() internal {
        if (vault.posture() != ghostPosture) {
            ++illegalPosture;
            ghostPosture = vault.posture();
        }
        if (vault.paused() != ghostPaused) {
            ++badAuthority;
            ghostPaused = vault.paused();
        }
    }

    function _scan(uint256[] memory idx)
        internal
        view
        returns (uint256 planners, uint256 trustees, bytes32 plannerLineage, bytes32 auditorLineage)
    {
        for (uint256 i = 0; i < idx.length; ++i) {
            GhostSigner memory g = ghostSigner[who[idx[i]]];
            if (g.role == IAmanahVault.Role.PLANNER) {
                ++planners;
                plannerLineage = g.lineage;
            } else if (g.role == IAmanahVault.Role.AUDITOR) {
                auditorLineage = g.lineage;
            } else if (g.role == IAmanahVault.Role.TRUSTEE && g.active) {
                ++trustees;
            }
        }
    }

    function _validRefusal(bytes32 anchorId, bytes32 proposalId) internal view returns (bool) {
        GhostAnchor memory a = ghostAnchor[anchorId];
        IAmanahVault.Role role = ghostSigner[a.signer].role;
        bool refusal = a.verdict == IAmanahVault.Verdict.REJECT || a.verdict == IAmanahVault.Verdict.ESCALATE;
        bool checker = role == IAmanahVault.Role.AUDITOR || role == IAmanahVault.Role.SENTINEL;
        return a.signer != address(0) && a.proposalId == proposalId && refusal && checker && !ghostRefusalUsed[anchorId];
    }

    function _isTwoTrusteeSet(uint256[] memory idx) internal view returns (bool) {
        for (uint256 i = 0; i < idx.length; ++i) {
            GhostSigner memory g = ghostSigner[who[idx[i]]];
            if (g.role != IAmanahVault.Role.TRUSTEE || !g.active) return false;
            for (uint256 j = 0; j < i; ++j) {
                if (idx[j] == idx[i]) return false;
            }
        }
        return idx.length >= 2;
    }

    function _activeTrustees() internal view returns (uint256 n) {
        for (uint256 i = 0; i < KEY_COUNT; ++i) {
            GhostSigner memory g = ghostSigner[who[i]];
            if (g.role == IAmanahVault.Role.TRUSTEE && g.active) ++n;
        }
    }

    // Setup without the fuzzer: two trustees sign each call

    function _setupRegister(uint256 i, IAmanahVault.Role role, bytes32 lineage) internal {
        Gov memory g =
            _setupGov(vault.ACTION_REGISTER_SIGNER(), keccak256(abi.encode(who[i], role, lineage, L.VIEW_NUMBERS)));
        vault.registerSigner(who[i], role, lineage, L.VIEW_NUMBERS, g.nonce, g.deadline, g.sigs);
        ghostSigner[who[i]] = GhostSigner(role, lineage, true);
    }

    function _setupMandate(bytes32 pid, IAmanahVault.Mandate memory m) internal {
        Gov memory g = _setupGov(vault.ACTION_SET_MANDATE(), keccak256(abi.encode(pid, m)));
        vault.setMandate(pid, m, g.nonce, g.deadline, g.sigs);
        ghostMandate[pid] = m;
    }

    function _setupBeneficiary(bytes32 pid, address wallet) internal {
        Gov memory g = _setupGov(vault.ACTION_ADD_BENEFICIARY(), keccak256(abi.encode(pid, wallet, bytes32(0))));
        vault.addBeneficiary(pid, wallet, bytes32(0), g.nonce, g.deadline, g.sigs);
        ghostActiveFrom[pid][wallet] = uint64(block.timestamp) + COOLING_OFF;
    }

    function _setupGov(bytes32 action, bytes32 paramsHash) internal returns (Gov memory g) {
        g.nonce = nextGovNonce++;
        g.deadline = block.timestamp + 1 hours;
        g.idx = _idx(TRUSTEE1, TRUSTEE2);
        bytes32 digest = vault.hashGovernance(action, paramsHash, g.nonce, g.deadline);
        g.sigs = new bytes[](2);
        g.sigs[0] = _sign(pk[TRUSTEE1], digest);
        g.sigs[1] = _sign(pk[TRUSTEE2], digest);
        usedGovNonces.push(g.nonce);
        govNonceSuccesses[g.nonce] = 1;
    }

    // Small helpers

    function _sign(uint256 key, bytes32 digest) internal pure returns (bytes memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(key, digest);
        return abi.encodePacked(r, s, v);
    }

    function _idx(uint256 a) internal pure returns (uint256[] memory r) {
        r = new uint256[](1);
        r[0] = a;
    }

    function _idx(uint256 a, uint256 b) internal pure returns (uint256[] memory r) {
        r = new uint256[](2);
        (r[0], r[1]) = (a, b);
    }

    function _idx(uint256 a, uint256 b, uint256 c) internal pure returns (uint256[] memory r) {
        r = new uint256[](3);
        (r[0], r[1], r[2]) = (a, b, c);
    }

    function _idx(uint256 a, uint256 b, uint256 c, uint256 d) internal pure returns (uint256[] memory r) {
        r = new uint256[](4);
        (r[0], r[1], r[2], r[3]) = (a, b, c, d);
    }

    function _idx(uint256 a, uint256 b, uint256 c, uint256 d, uint256 e) internal pure returns (uint256[] memory r) {
        r = new uint256[](5);
        (r[0], r[1], r[2], r[3], r[4]) = (a, b, c, d, e);
    }
}
