#!/usr/bin/env bash
# Drives the contract-level demo scenarios against the Anvil fixture with cast (plan task A5):
# a routine payout (6), a forced attack to an unlisted wallet (10), a same-lineage quorum (11),
# the planner adding a beneficiary (12) and a guardian pause with a two-trustee unpause (16).
# Signatures come from `cast wallet sign` over typed data built from shared/eip712.json. Reverting
# calls go out with a fixed gas limit, so each is mined and has a hash, as plan task B3 needs.
#
#   anvil
#   forge script script/Fixture.s.sol --rpc-url http://127.0.0.1:8545 --broadcast
#   bash script/anvil_smoke.sh
#
# Keys default to Anvil's accounts, as in the fixture; set PLANNER_KEY and so on to override.
set -euo pipefail
cd "$(dirname "$0")/.."

rpc="${ANVIL_RPC_URL:-http://127.0.0.1:8545}"
mnemonic="test test test test test test test test test test test junk"
anvil_key() { cast wallet private-key --mnemonic "$mnemonic" --mnemonic-index "$1"; }
relayer=$(anvil_key 0)
planner=${PLANNER_KEY:-$(anvil_key 1)}
auditor=${AUDITOR_KEY:-$(anvil_key 2)}
sentinel=${SENTINEL_KEY:-$(anvil_key 3)}
trustee1=${TRUSTEE1_KEY:-$(anvil_key 5)}
trustee2=${TRUSTEE2_KEY:-$(anvil_key 6)}
guardian=${GUARDIAN_KEY:-$(anvil_key 8)}
control_auditor=${CONTROL_AUDITOR_KEY:-$(anvil_key 9)}

field() { python3 -c "import json,sys; d=json.load(open('deployments/31337.json')); print(eval('d' + sys.argv[1]))" "$1"; }
vault=$(field "['vault']")
zkt=$(field "['programmes']['ZKT-IPOH-FAKIR-M']")
data_dir=$(field "['dataDir']")
payout_sig="execute((bytes32,bytes32,address,uint256,bytes32,uint256,uint256),bytes[])"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# Move to a fresh vault day (past the fixture's 60-second cooling-off too), so runs do not add up.
cast rpc evm_increaseTime 86400 --rpc-url "$rpc" > /dev/null
cast rpc evm_mine --rpc-url "$rpc" > /dev/null
now=$(cast block latest --field timestamp --rpc-url "$rpc")
deadline=$((now + 3600))

# The zakat household with the most room under its 30-day cap; this run pays it 300 USDC.
household=""
least=""
for w in $(python3 -c "import json; print(' '.join(b['wallet'] for b in json.load(open('$data_dir/beneficiaries.json'))['beneficiaries'] if b['programme_code'] == 'ZKT-IPOH-FAKIR-M'))"); do
    spent=$(cast call "$vault" "spentThisPeriod(bytes32,address)(uint256)" "$zkt" "$w" --rpc-url "$rpc" | cut -d' ' -f1)
    if [ -z "$least" ] || [ "$spent" -lt "$least" ]; then least=$spent; household=$w; fi
done
if [ "$least" -gt 100000000 ]; then echo "every household is near its cap; restart anvil and the fixture"; exit 1; fi

# typed_data <primaryType> <message json> writes an EIP-712 document from shared/eip712.json.
typed_data() {
    python3 - "$1" "$2" "$vault" > "$work/typed.json" <<'PY'
import json, sys
primary, message, vault = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]
shared = json.load(open("../shared/eip712.json"))
domain = {**shared["domain"], "chainId": 31337, "verifyingContract": vault}
types = {"EIP712Domain": [{"name": "name", "type": "string"}, {"name": "version", "type": "string"},
                          {"name": "chainId", "type": "uint256"}, {"name": "verifyingContract", "type": "address"}],
         primary: shared["types"][primary]}
print(json.dumps({"types": types, "primaryType": primary, "domain": domain, "message": message}))
PY
}

sign_all() {  # sign_all <key>... prints a cast array of signatures over $work/typed.json
    local sigs=()
    for k in "$@"; do sigs+=("$(cast wallet sign --data --from-file "$work/typed.json" --private-key "$k")"); done
    local IFS=,
    echo "[${sigs[*]}]"
}

payout() {  # payout <nonce> <wallet> <amount in base units>; sets $tuple and writes the typed data
    local proposal evidence
    proposal=$(cast keccak "smoke-proposal-$1")
    evidence=$(cast keccak "smoke-evidence-$1")
    tuple="($proposal,$zkt,$2,$3,$evidence,$1,$deadline)"
    typed_data Payout "{\"proposalId\":\"$proposal\",\"programmeId\":\"$zkt\",\"beneficiary\":\"$2\",\"amount\":\"$3\",\"evidenceHash\":\"$evidence\",\"nonce\":\"$1\",\"deadline\":\"$deadline\"}"
}

governance() {  # governance <action name> <paramsHash> <govNonce>; writes the typed data
    typed_data Governance "{\"action\":\"$(cast keccak "$1")\",\"paramsHash\":\"$2\",\"govNonce\":\"$3\",\"deadline\":\"$deadline\"}"
}

failures=0
hash=""
call_from=""
call_args=()

send() {  # send <from key> <args...>; a fixed gas limit so a reverting call is still mined
    call_from=$(cast wallet address --private-key "$1")
    call_args=("${@:2}")
    hash=$(cast send "$vault" "${@:2}" --private-key "$1" --gas-limit 1000000 --rpc-url "$rpc" --json \
        | python3 -c "import json,sys; print(json.load(sys.stdin)['transactionHash'])")
}

report() {  # report <scenario> <expected> <wanted status> <wanted error or ->, for the last send
    local status error=- verdict=ok
    status=$(cast receipt "$hash" status --rpc-url "$rpc")
    [ "$status" = "true" ] && status=success || status=reverted
    if [ "$3" = reverted ]; then
        # Replay the call on the block before it was mined to read the error it reverted with.
        local block
        block=$(($(cast receipt "$hash" blockNumber --rpc-url "$rpc") - 1))
        error=$(cast call "$vault" "${call_args[@]}" --from "$call_from" --block "$block" --rpc-url "$rpc" 2>&1 \
            | grep -oE 'data: "0x[0-9a-fA-F]{8}' | cut -c8- || true)
        [ "$error" = "$(cast sig "$4()")" ] && error="$4" || error="unexpected:$error"
    fi
    if [ "$status" != "$3" ] || [ "$error" != "$4" ]; then verdict=FAIL; failures=$((failures + 1)); fi
    printf '%-4s %-44s %-8s %-16s %s %s\n' "$1" "$2" "$status" "$error" "$hash" "$verdict"
}

printf '%-4s %-44s %-8s %-16s %s\n' "#" "scenario" "status" "error" "transaction"
# Nonces from the block time, so the script can run again on the same node.
n=$((now * 10))

payout $((n + 1)) "$household" 150000000
send "$relayer" "$payout_sig" "$tuple" "$(sign_all "$planner" "$auditor" "$sentinel")"
report 6 "routine payout, planner, auditor, sentinel" success -

payout $((n + 2)) "$(cast wallet new --json | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["address"])')" 2000000000
send "$relayer" "$payout_sig" "$tuple" "$(sign_all "$planner" "$auditor" "$sentinel")"
report 10 "forced attack to an unlisted wallet" reverted NotAllowlisted

payout $((n + 3)) "$household" 150000000
send "$relayer" "$payout_sig" "$tuple" "$(sign_all "$planner" "$control_auditor" "$sentinel")"
report 11 "same-lineage quorum, two Claude keys" reverted SameLineage

stranger=0x000000000000000000000000000000000000dEaD
id_hash=$(cast keccak "smoke-id")
params=$(cast keccak "$(cast abi-encode "f(bytes32,address,bytes32)" "$zkt" "$stranger" "$id_hash")")
governance addBeneficiary "$params" $((n + 4))
send "$planner" "addBeneficiary(bytes32,address,bytes32,uint256,uint256,bytes[])" "$zkt" "$stranger" "$id_hash" \
    $((n + 4)) "$deadline" "$(sign_all "$planner")"
report 12 "planner adds a beneficiary with its own key" reverted NotTrustee

send "$guardian" "pause()"
report 16a "guardian pauses" success -
payout $((n + 5)) "$household" 150000000
sigs=$(sign_all "$planner" "$auditor" "$sentinel")
send "$relayer" "$payout_sig" "$tuple" "$sigs"
report 16b "payout while paused" reverted EnforcedPause
governance unpause "$(cast keccak 0x)" $((n + 6))
send "$relayer" "unpause(uint256,uint256,bytes[])" $((n + 6)) "$deadline" "$(sign_all "$trustee1" "$trustee2")"
report 16c "two trustees unpause" success -
send "$relayer" "$payout_sig" "$tuple" "$sigs"
report 16d "the same payout after unpause" success -

echo "household balance: $(cast call "$(field "['usdc']")" "balanceOf(address)(uint256)" "$household" --rpc-url "$rpc")"
[ "$failures" -eq 0 ] && echo "all scenarios behaved as expected" || { echo "$failures scenario(s) did not"; exit 1; }
