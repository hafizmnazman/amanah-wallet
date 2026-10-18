#!/usr/bin/env bash
# Writes the contract ABIs that other lanes build against into shared/abi/.
# Run after every contract change:  bash contracts/script/abi.sh
# Check that the committed files are current:  bash contracts/script/abi.sh --check
set -euo pipefail

cd "$(dirname "$0")/.."
out_dir=../shared/abi
mkdir -p "$out_dir"
forge build --quiet

# Until src/AmanahVault.sol exists, publish the interface ABI under the vault's name (task A1).
vault=src/AmanahVault.sol:AmanahVault
[ -f src/AmanahVault.sol ] || vault=src/IAmanahVault.sol:IAmanahVault

targets=("$vault=AmanahVault.json")
[ -f src/mocks/MockUSDC.sol ] && targets+=("src/mocks/MockUSDC.sol:MockUSDC=MockUSDC.json")

stale=0
for t in "${targets[@]}"; do
    contract="${t%%=*}"
    file="$out_dir/${t#*=}"
    abi="$(forge inspect "$contract" abi --json)"
    if [ "${1:-}" = "--check" ]; then
        if [ "$abi" != "$(cat "$file" 2>/dev/null)" ]; then
            echo "stale: $file (run bash contracts/script/abi.sh)"
            stale=1
        fi
    else
        printf '%s\n' "$abi" > "$file"
        echo "wrote $file from $contract"
    fi
done
exit "$stale"
