#!/usr/bin/env bash
# Runs every suite in the repository and prints one line per suite (the README's testing section).
#
#   bash scripts/test_all.sh            # everything, about 3 minutes
#   bash scripts/test_all.sh --quick    # without the browser checks and the Anvil demo
#
# PYTHON picks the interpreter; the default is .venv/bin/python. Anvil and forge must be on PATH, and
# frontend/node_modules must exist (cd frontend && npm ci). The exit code is 1 if any suite fails.
set -uo pipefail
python="${PYTHON:-}"
if [[ "$python" == */* && "$python" != /* ]]; then python="$PWD/$python"; fi
cd "$(dirname "$0")/.."
[ -n "$python" ] || python="$PWD/.venv/bin/python"
[ -x "$python" ] || python=python3
quick=0
[ "${1:-}" = "--quick" ] && quick=1
failed=0

# run <name> <pattern for the summary line> <command...>
run() {
    local name="$1" pattern="$2"
    shift 2
    local out status
    out=$("$@" 2>&1)
    status=$?
    local line
    # Colour codes (vitest and Vite print them on CI) would split the summary line, so they go first
    line=$(printf '%s\n' "$out" | sed 's/\x1b\[[0-9;]*m//g' | grep -E "$pattern" | tail -1 | sed 's/^[[:space:]]*//')
    if [ "$status" -eq 0 ]; then
        echo "pass  $name: ${line:-done}"
    else
        echo "FAIL  $name: ${line:-exit $status}"
        printf '%s\n' "$out" | tail -20 | sed 's/^/      /'
        failed=1
    fi
}

run "contracts" "tests passed|failed" bash -c "cd contracts && forge test"
run "backend" "passed|failed" bash -c "cd backend && '$python' -m pytest -q"
run "red team" "passed|failed" "$python" -m pytest -q -c redteam/pytest.ini redteam/tests
run "release scripts" "passed|failed" "$python" -m pytest -q -p no:cacheprovider scripts/tests
run "frontend build" "built in|error" bash -c "cd frontend && npm run build"
run "frontend unit" "Tests +[0-9]" bash -c "cd frontend && npm test"
if [ "$quick" -eq 0 ]; then
    run "frontend browser, mock" "passed|failed" bash -c "cd frontend && npx playwright test"
    run "frontend browser, real stack" "passed|failed" bash -c "cd frontend && PYTHON='$python' npx playwright test --config playwright.stack.config.ts"
    run "demo on Anvil" "checks as expected" "$python" scripts/run_demo.py --network anvil
fi
exit "$failed"
