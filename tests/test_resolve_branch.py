# tests/test_resolve_branch.py
# Fail-closed branch resolution — no hardcoded main/base fallbacks.

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import resolve_branch as rb  # noqa: E402


class ResolveBranchTests(unittest.TestCase):
    def test_explicit_env_used_when_exists(self):
        with mock.patch.object(rb, "list_branches", return_value=["base", "main"]):
            with mock.patch.dict(os.environ, {"BASE_BRANCH": "base"}, clear=False):
                # clear competing keys
                os.environ.pop("PASSPORT_BRANCH", None)
                os.environ.pop("GIT_BRANCH", None)
                branch, source = rb.resolve_branch("Appel420", "Passport")
        self.assertEqual(branch, "base")
        self.assertEqual(source, "env:BASE_BRANCH")

    def test_explicit_env_missing_branch_is_deny(self):
        with mock.patch.object(rb, "list_branches", return_value=["main"]):
            with mock.patch.dict(os.environ, {"BASE_BRANCH": "base"}, clear=False):
                os.environ.pop("PASSPORT_BRANCH", None)
                os.environ.pop("GIT_BRANCH", None)
                with self.assertRaises(rb.BranchResolutionError) as ctx:
                    rb.resolve_branch("Appel420", "Passport")
        self.assertIn("DENY", str(ctx.exception))

    def test_default_branch_when_no_env(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("BASE_BRANCH", "PASSPORT_BRANCH", "GIT_BRANCH")}
        with mock.patch.object(rb, "list_branches", return_value=["trunk", "dev"]):
            with mock.patch.object(rb, "api_default_branch", return_value="trunk"):
                with mock.patch.dict(os.environ, env, clear=True):
                    branch, source = rb.resolve_branch("o", "r")
        self.assertEqual(branch, "trunk")
        self.assertEqual(source, "api:default_branch")

    def test_default_branch_not_in_list_is_deny(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("BASE_BRANCH", "PASSPORT_BRANCH", "GIT_BRANCH")}
        with mock.patch.object(rb, "list_branches", return_value=["dev"]):
            with mock.patch.object(rb, "api_default_branch", return_value="main"):
                with mock.patch.dict(os.environ, env, clear=True):
                    with self.assertRaises(rb.BranchResolutionError) as ctx:
                        rb.resolve_branch("o", "r")
        self.assertIn("DENY", str(ctx.exception))

    def test_no_first_branch_fallback(self):
        """Ambiguous state must not pick branches[0]."""
        env = {k: v for k, v in os.environ.items()
               if k not in ("BASE_BRANCH", "PASSPORT_BRANCH", "GIT_BRANCH")}
        with mock.patch.object(rb, "list_branches", return_value=["aaa", "bbb"]):
            with mock.patch.object(
                rb, "api_default_branch",
                side_effect=rb.BranchResolutionError("DENY: default_branch missing"),
            ):
                with mock.patch.dict(os.environ, env, clear=True):
                    with self.assertRaises(rb.BranchResolutionError):
                        rb.resolve_branch("o", "r")


if __name__ == "__main__":
    unittest.main()
