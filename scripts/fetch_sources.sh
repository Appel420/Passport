#!/usr/bin/env bash
# Fetch Passport sources without hardcoding any branch name.
# Fail closed if branch cannot be resolved.
set -euo pipefail

OWNER="${OWNER:-Appel420}"
REPO="${REPO:-Passport}"
DEST="${DEST:-./passport-src}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

BRANCH="$(python3 "${ROOT}/scripts/resolve_branch.py" --quiet "${OWNER}" "${REPO}")" || {
  echo "DENY: branch resolution failed for ${OWNER}/${REPO}" >&2
  exit 1
}

echo "evidence: resolved_branch=${BRANCH} repo=${OWNER}/${REPO} outcome=ALLOW"
mkdir -p "${DEST}/tests"
BASE_URL="https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}"
for path in verify.py provenance.py tests/test_verify.py tests/test_provenance.py; do
  curl -fsSL "${BASE_URL}/${path}" -o "${DEST}/${path}"
  echo "got ${path}"
done
