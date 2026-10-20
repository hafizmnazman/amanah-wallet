#!/usr/bin/env bash
# Reproduces Amanah's published numbers on one machine.
#
#   bash scripts/reproduce.sh            # the suites, the Anvil demo, the red team's reports and the app's numbers from their rows
#   bash scripts/reproduce.sh --chain    # also re-checks Base Sepolia: every payout and the ERC-8004 agents (RPC_URL in .env)
#   bash scripts/reproduce.sh --fisco    # also the vault on a fresh FISCO BCOS chain (downloads FISCO 3.17.1, about 75 MB)
#
# Needs no model key: the demo runs with dry-run models, and the red team's numbers are rendered again from the
# committed results.jsonl, so no answer is asked of any model. The exit code is 1 if anything differs.
set -uo pipefail
cd "$(dirname "$0")/.."
python="${PYTHON:-$PWD/.venv/bin/python}"
[ -x "$python" ] || python=python3
chain=0
fisco=0
for arg in "$@"; do
  case "$arg" in
    --chain) chain=1 ;;
    --fisco) fisco=1 ;;
    *) echo "unknown option $arg" >&2; exit 2 ;;
  esac
done
failed=0

echo "== Every test suite, and the 16 scenarios on a fresh Anvil"
bash scripts/test_all.sh || failed=1

echo
echo "== The red team's published reports, rendered again from their rows"
for run in final domestic-kimi zh-kimi; do
  copy=$(mktemp -d)
  cp -r "redteam/results/$run/." "$copy/"
  "$python" -m redteam.report "$copy" >/dev/null
  if diff -q "$copy/report.md" "redteam/results/$run/report.md" >/dev/null; then
    echo "pass  $run: report.md renders byte for byte from results.jsonl"
  else
    echo "FAIL  $run: report.md differs from what its rows give"
    failed=1
  fi
done

echo
echo "== The app's numbers, generated again from the run files"
"$python" scripts/export_ui_data.py >/dev/null
if git diff --quiet -- frontend/src/data/facts.json; then
  echo "pass  frontend/src/data/facts.json is what the committed run files give"
else
  echo "FAIL  frontend/src/data/facts.json differs from what the committed run files give"
  failed=1
fi

if [ "$chain" = 1 ]; then
  echo
  echo "== Base Sepolia, from the chain alone"
  "$python" scripts/verify.py --csv evidence/transactions.csv 2>&1 | tail -1 | sed -E 's#https?://[^ ]*#<rpc>#g' || failed=1
  "$python" scripts/register_agents.py --check 2>&1 | cut -c1-120 | sed -E 's#https?://[^ ]*#<rpc>#g' || failed=1
fi

if [ "$fisco" = 1 ]; then
  echo
  echo "== FISCO BCOS, WeBank's consortium chain"
  # A fresh chain each run, keeping the downloaded node: the fixture cannot be deployed again on an earlier
  # run's chain. The old chain is moved aside, not deleted, and the node is stopped at the end.
  fdir="${FISCO_DIR:-$HOME/fisco}"
  if [ -d "$fdir/nodes" ]; then
    bash "$fdir/nodes/127.0.0.1/stop_all.sh" >/dev/null 2>&1 || true
    mv "$fdir/nodes" "$fdir/nodes.$(date +%Y%m%d-%H%M%S)"
  fi
  bash scripts/fisco_up.sh || failed=1
  (cd contracts && FISCO_LOCAL=1 forge script script/Fixture.s.sol --rpc-url http://127.0.0.1:8546 --broadcast --legacy --slow \
    | grep -E "ONCHAIN EXECUTION|Error") || failed=1
  "$python" scripts/fisco_demo.py --evidence "$(mktemp -d)" | tail -6 || failed=1
  bash "$fdir/nodes/127.0.0.1/stop_all.sh" >/dev/null 2>&1 || true
fi

echo
[ "$failed" = 0 ] && echo "Everything reproduced." || echo "Something did not reproduce; see FAIL above."
exit "$failed"
