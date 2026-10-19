#!/usr/bin/env bash
# Decision E-31: a one-node FISCO BCOS chain, WeBank's consortium chain, that the unchanged contracts run on
# through its Web3 JSON-RPC.
#
#   bash scripts/fisco_up.sh            # builds and starts the chain in ~/fisco, Web3 RPC on 127.0.0.1:8546
#   (cd contracts && FISCO_LOCAL=1 forge script script/Fixture.s.sol --rpc-url http://127.0.0.1:8546 --broadcast --legacy --slow)
#   .venv/bin/python scripts/fisco_demo.py
#
# Two things differ from Ethereum, and both are settings, not code:
# - the Web3 RPC is off in a new node's config.ini; this script turns it on, on port 8546 (8545 is Anvil's);
# - the EVM's block.timestamp is in milliseconds until the chain's feature_evm_timestamp flag is set, while
#   the Web3 RPC's block headers already report seconds. The vault counts days and 30-day periods in seconds,
#   so this script sets the flag with one Web3 transaction to the system-config precompile at 0x1000.
# The genesis block's timestamp is 0, so the fixture is deployed after the first block (the flag's).
# One thing does not carry over: eth_call answers from the latest state whatever block it names, so verify.py,
# which reads the vault as it was at the block before each payout, cannot run here. The node's
# enable_separate_block_state keeps each block's state, but with it on, 3.17.1's Web3 RPC returned no blocks at
# all (tested 20 October 2026), so it stays off.
set -euo pipefail

VERSION="${FISCO_VERSION:-v3.17.1}"
DIR="${FISCO_DIR:-$HOME/fisco}"
RPC="http://127.0.0.1:8546"
MNEMONIC="test test test test test test test test test test test junk"

mkdir -p "$DIR"
cd "$DIR"
if [ ! -x ./fisco-bcos ]; then
  curl -sSL -o build_chain.sh "https://github.com/FISCO-BCOS/FISCO-BCOS/releases/download/$VERSION/build_chain.sh"
  curl -sSL -o fisco-bcos.tar.gz "https://github.com/FISCO-BCOS/FISCO-BCOS/releases/download/$VERSION/fisco-bcos-linux-x86_64.tar.gz"
  tar -xzf fisco-bcos.tar.gz
fi
./fisco-bcos -v | head -1

if [ ! -d nodes ]; then
  bash build_chain.sh -l 127.0.0.1:1 -p 30300,20200 -o nodes -e ./fisco-bcos
  python3 - nodes/127.0.0.1/node0/config.ini <<'EOF'
import sys
path = sys.argv[1]
text = open(path).read()
head, web3 = text.split("[web3_rpc]", 1)
web3 = (web3.replace("enable=false", "enable=true", 1).replace("listen_ip=0.0.0.0", "listen_ip=127.0.0.1", 1)
        .replace("listen_port=8545", "listen_port=8546", 1))
open(path, "w").write(head + "[web3_rpc]" + web3)
EOF
fi
bash nodes/127.0.0.1/start_all.sh

for _ in $(seq 1 30); do
  cast chain-id --rpc-url "$RPC" >/dev/null 2>&1 && break
  sleep 1
done
echo "chain id $(cast chain-id --rpc-url "$RPC")"

SYSTEM_CONFIG=0x0000000000000000000000000000000000001000
current=$(cast call "$SYSTEM_CONFIG" "getValueByKey(string)(string,int256)" feature_evm_timestamp --rpc-url "$RPC" | head -1)
if [ "$current" != '"1"' ]; then
  key=$(cast wallet private-key --mnemonic "$MNEMONIC" --mnemonic-index 0)
  cast send --private-key "$key" --rpc-url "$RPC" --legacy --gas-limit 1000000 "$SYSTEM_CONFIG" \
    "setValueByKey(string,string)" feature_evm_timestamp 1 >/dev/null
fi
echo "feature_evm_timestamp $(cast call "$SYSTEM_CONFIG" "getValueByKey(string)(string,int256)" feature_evm_timestamp --rpc-url "$RPC" | head -1)"
