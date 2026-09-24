#!/usr/bin/env bash
# Fetch Passport files without hardcoding main.
# Prefers branch 'base', then API default_branch, then first branch.
set -euo pipefail

OWNER="${OWNER:-Appel420}"
REPO="${REPO:-Passport}"
DEST="${DEST:-./passport-src}"

BRANCH="${PASSPORT_BRANCH:-${GIT_BRANCH:-}}"
if [[ -z "${BRANCH}" ]]; then
  BRANCHES=$(python3 - <<PY
import json, urllib.request
req = urllib.request.Request(
    "https://api.github.com/repos/${OWNER}/${REPO}/branches",
    headers={"Accept": "application/vnd.github+json", "User-Agent": "passport-fetch"},
)
with urllib.request.urlopen(req, timeout=20) as r:
    data = json.load(r)
print(" ".join(b["name"] for b in data))
PY
)
  if echo " ${BRANCHES} " | grep -q " base "; then
    BRANCH=base
  else
    BRANCH=$(python3 - <<PY
import json, urllib.request
req = urllib.request.Request(
    "https://api.github.com/repos/${OWNER}/${REPO}",
    headers={"Accept": "application/vnd.github+json", "User-Agent": "passport-fetch"},
)
with urllib.request.urlopen(req, timeout=20) as r:
    print(json.load(r).get("default_branch", "base"))
PY
)
  fi
fi

echo "using branch: ${BRANCH}"
mkdir -p "${DEST}/tests"
BASE_URL="https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}"
for path in verify.py provenance.py tests/test_verify.py tests/test_provenance.py; do
  curl -fsSL "${BASE_URL}/${path}" -o "${DEST}/${path}"
  echo "got ${path}"
done
