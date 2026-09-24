#!/usr/bin/env python3
"""Resolve the integration branch for Appel420/Passport (or any owner/repo).

Never hardcodes main. Preference order:
  1. PASSPORT_BRANCH / GIT_BRANCH env
  2. remote branch named 'base' if it exists
  3. API default_branch
  4. first listed branch
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from typing import List, Optional


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
        return []
    return [b["name"] for b in data if isinstance(b, dict) and "name" in b]


def api_default_branch(owner: str, repo: str) -> Optional[str]:
    data = _get_json(f"https://api.github.com/repos/{owner}/{repo}")
    if isinstance(data, dict):
        db = data.get("default_branch")
        if isinstance(db, str) and db:
            return db
    return None


def resolve_branch(owner: str = "Appel420", repo: str = "Passport") -> str:
    env = os.environ.get("PASSPORT_BRANCH") or os.environ.get("GIT_BRANCH")
    if env:
        return env.strip()

    branches = list_branches(owner, repo)
    if "base" in branches:
        return "base"

    default = api_default_branch(owner, repo)
    if default and (not branches or default in branches):
        return default

    if branches:
        return branches[0]

    raise RuntimeError(f"could not resolve branch for {owner}/{repo}")


def raw_url(owner: str, repo: str, path: str, branch: Optional[str] = None) -> str:
    b = branch or resolve_branch(owner, repo)
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{b}/{path.lstrip('/')}"


if __name__ == "__main__":
    owner = sys.argv[1] if len(sys.argv) > 1 else "Appel420"
    repo = sys.argv[2] if len(sys.argv) > 2 else "Passport"
    branch = resolve_branch(owner, repo)
    print(branch)
    if "--url" in sys.argv:
        path = sys.argv[sys.argv.index("--url") + 1]
        print(raw_url(owner, repo, path, branch))
