#!/usr/bin/env bash
# Builds the hosted demo (the frontend in mock mode: recorded data in the browser, no keys, no chain) from a
# committed revision, never the working tree, and stages it as Vercel's Build Output API v3 for
# `vercel deploy --prebuilt`. Every run uses fresh folders, so nothing is deleted.
#
#   bash scripts/build_demo.sh [REV] [STAGE_PARENT]      # REV defaults to HEAD, STAGE_PARENT to /tmp
#   BASE=/amanah-wallet/ bash scripts/build_demo.sh ...    # the GitHub Pages mirror, served under that path
#
# With a BASE other than "/", the stage is a plain static folder for GitHub Pages instead: the app with a 404.html
# copy of index.html (so a deep link opens the app) and a .nojekyll file.
#
# Then, from a shell where the Vercel CLI is logged in (on this machine, Windows), in the printed stage folder:
#   VERCEL_ORG_ID=<team id> VERCEL_PROJECT_ID=<project id> npx vercel@64.7.0 deploy --prebuilt --prod --yes
# The project's root directory setting is `frontend`, so the stage holds an empty `frontend/` folder for the CLI.
set -euo pipefail
REV="${1:-HEAD}"
PARENT="${2:-/tmp}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
SHA=$(git rev-parse --short "$REV")
SRC=$(mktemp -d /tmp/demo-src.XXXXXX)
OUT=$(mktemp -d /tmp/demo-dist.XXXXXX)
STAGE="$PARENT/amanah-demo-$SHA-$(date +%H%M%S)"
echo "building $SHA in $SRC"
if git ls-tree -r --name-only "$REV" frontend | grep -E '(^|/)\.env($|\.)' | grep -v example; then
  echo "a committed .env file is in frontend; stop"; exit 1
fi
git archive "$REV" frontend | tar -x -C "$SRC"
ln -s "$REPO/frontend/node_modules" "$SRC/frontend/node_modules"
for v in $(env | grep -o '^VITE_[A-Z_]*' || true); do unset "$v"; done
cd "$SRC/frontend"
BASE="${BASE:-/}"
VITE_MOCK_API=1 VITE_MOCK_LATENCY_MS=350 VITE_DEV_SIGNING=1 VITE_CHAIN_ID=84532 VITE_VAULT_ADDRESS= \
  npx vite build --base "$BASE" --outDir "$OUT" --emptyOutDir --logLevel warn
# The dev trustee key of the local test chain must never be in a public bundle
K=$(cast wallet private-key --mnemonic "test test test test test test test test test test test junk" --mnemonic-index 5)
if grep -q "${K#0x}" "$OUT"/assets/*.js; then echo "dev key in the bundle; stop"; exit 1; fi
if [ "$BASE" != "/" ]; then
  PAGES="$PARENT/amanah-pages-$SHA-$(date +%H%M%S)"
  mkdir -p "$PAGES"
  tar -C "$OUT" --exclude=./vercel.json -cf - . | tar -C "$PAGES" -xf -
  cp "$PAGES/index.html" "$PAGES/404.html"
  touch "$PAGES/.nojekyll"
  echo "$SHA" > "$PAGES/version.txt"
  echo "pages: $PAGES"
  exit 0
fi
mkdir -p "$STAGE/.vercel/output/static" "$STAGE/frontend"
# vercel.json is not read by the Build Output API; config.json below does its job
tar -C "$OUT" --exclude=./vercel.json -cf - . | tar -C "$STAGE/.vercel/output/static" -xf -
cat > "$STAGE/.vercel/output/config.json" <<'JSON'
{
  "version": 3,
  "routes": [
    { "src": "^/assets/(.*)$", "headers": { "cache-control": "public, max-age=31536000, immutable" }, "continue": true },
    { "handle": "filesystem" },
    { "src": "^/assets/.*$", "status": 404 },
    { "src": "^/(.*)$", "dest": "/index.html" }
  ]
}
JSON
echo "$SHA" > "$STAGE/.vercel/output/static/version.txt"
( cd "$STAGE/.vercel/output/static" && find . -type f | sort | xargs ls -l | awk '{s+=$5} END {print NR " files, " s " bytes"}' )
echo "stage: $STAGE"
