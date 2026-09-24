#!/usr/bin/env python3
"""Resolve a repository branch without hardcoding names.

Contract (fail closed):
  1. Explicit BASE_BRANCH / PASSPORT_BRANCH / GIT_BRANCH env
  2. Else GitHub API default_branch
  3. Else DENY

The chosen name is always verified against the remote branch list.
No fallback to main, master, base, develop, or first-listed branch.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import List, Optional, Tuple


class BranchResolutionError(RuntimeError):
    """Fail-closed branch resolution failure."""


def _get_json(url: str) -> object:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "passport-resolve-branch",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def list_branches(owner: str, repo: str) -> List[str]:
    data = _get_json(f"https://api.github.com/repos/{owner}/{repo}/branches")
    if not isinstance(data, list):
        raise BranchResolutionError(
            f"DENY: branch list malformed for {owner}/{repo}"
        )
    names = [b["name"] for b in data if isinstance(b, dict) and "name" in b]
    if not names:
        raise BranchResolutionError(
            f"DENY: no branches returned for {owner}/{repo}"
        )
    return names


def api_default_branch(owner: str, repo: str) -> str:
    data = _get_json(f"https://api.github.com/repos/{owner}/{repo}")
    if not isinstance(data, dict):
        raise BranchResolutionError(
            f"DENY: repo metadata malformed for {owner}/{repo}"
        )
    db = data.get("default_branch")
    if not isinstance(db, str) or not db.strip():
        raise BranchResolutionError(
            f"DENY: default_branch missing for {owner}/{repo}"
        )
    return db.strip()


def _explicit_from_env() -> Optional[str]:
    for key in ("BASE_BRANCH", "PASSPORT_BRANCH", "GIT_BRANCH"):
        val = os.environ.get(key)
        if val and val.strip():
            return val.strip()
    return None


def resolve_branch(
    owner: str = "Appel420",
    repo: str = "Passport",
) -> Tuple[str, str]:
    """Return (branch, source) or raise BranchResolutionError.

    source is 'env:BASE_BRANCH' | 'env:PASSPORT_BRANCH' | 'env:GIT_BRANCH'
    or 'api:default_branch'.
    """
    try:
        branches = list_branches(owner, repo)
    except urllib.error.URLError as e:
        raise BranchResolutionError(
            f"DENY: cannot list branches for {owner}/{repo}: {e}"
        ) from e

    explicit = None
    source = None
    for key in ("BASE_BRANCH", "PASSPORT_BRANCH", "GIT_BRANCH"):
        val = os.environ.get(key)
        if val and val.strip():
            explicit = val.strip()
            source = f"env:{key}"
            break

    if explicit is not None:
        if explicit not in branches:
            raise BranchResolutionError(
                f"DENY: explicit branch {explicit!r} via {source} "
                f"does not exist on {owner}/{repo}; known={branches}"
            )
        return explicit, source  # type: ignore[return-value]

    try:
        default = api_default_branch(owner, repo)
    except urllib.error.URLError as e:
        raise BranchResolutionError(
            f"DENY: cannot read default_branch for {owner}/{repo}: {e}"
        ) from e

    if default not in branches:
        raise BranchResolutionError(
            f"DENY: API default_branch {default!r} not in remote branches "
            f"for {owner}/{repo}; known={branches}"
        )
    return default, "api:default_branch"


def raw_url(
    owner: str,
    repo: str,
    path: str,
    branch: Optional[str] = None,
) -> str:
    if branch is None:
        branch, _ = resolve_branch(owner, repo)
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path.lstrip('/')}"


if __name__ == "__main__":
    owner = sys.argv[1] if len(sys.argv) > 1 else "Appel420"
    repo = sys.argv[2] if len(sys.argv) > 2 else "Passport"
    quiet = "--quiet" in sys.argv
    try:
        branch, source = resolve_branch(owner, repo)
    except BranchResolutionError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    if quiet:
        print(branch)
    else:
        print(branch)
        print(f"# evidence source={source} outcome=ALLOW repo={owner}/{repo}", file=sys.stderr)
    if "--url" in sys.argv:
        idx = sys.argv.index("--url")
        path = sys.argv[idx + 1]
        print(raw_url(owner, repo, path, branch))
