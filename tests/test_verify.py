# tests/test_verify.py
# Zero-dependency tests for verify.py

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from verify import (
    verify_passport_token,
    verify_provenance_record,
    reset_nonce_registry,
    default_opt_in,
    PASSPORT_VERSION,
)


def _valid_token(**overrides):
    now = int(time.time())
    token = {
        "passport_version": PASSPORT_VERSION,
        "owner": {"account_id": "Appel420", "display_name": "Derek Appel"},
        "issued_at": now - 10,
        "expires_at": now + 3600,
        "nonce": f"nonce-{now}-{id(overrides)}",
        "builds": [
            {
                "build_id": "passport",
                "name": "Passport",
                "first_seen": "2026-09-24T22:30:00Z",
                "attribution": "lead",
            }
        ],
        "signature": {
            "algorithm": "Ed25519",
            "value": "<base64-encoded-signature>",
            "public_key": "<base64-encoded-public-key>",
        },
    }
    token.update(overrides)
    return token


def test_token_rejects_bad_version():
    reset_nonce_registry()
    t = _valid_token(passport_version="9.9.9")
    r = verify_passport_token(t, require_signature=False)
    assert r.ok is False and r.stage == "version"


def test_token_rejects_missing_fields():
    reset_nonce_registry()
    t = _valid_token()
    del t["nonce"]
    r = verify_passport_token(t, require_signature=False)
    assert r.ok is False and r.stage == "required_fields"


def test_token_rejects_expired():
    reset_nonce_registry()
    now = int(time.time())
    t = _valid_token(issued_at=now - 100, expires_at=now - 1)
    r = verify_passport_token(t, require_signature=False, now=now)
    assert r.ok is False and r.stage == "timestamp"


def test_token_rejects_replay():
    reset_nonce_registry()
    t = _valid_token(nonce="fixed-nonce-replay-test")
    r1 = verify_passport_token(t, require_signature=False)
    assert r1.ok is True
    r2 = verify_passport_token(t, require_signature=False)
    assert r2.ok is False and r2.stage == "nonce"


def test_token_rejects_placeholder_signature():
    reset_nonce_registry()
    t = _valid_token()
    r = verify_passport_token(t, require_signature=True)
    assert r.ok is False and r.stage == "signature"


def test_token_owner_binding():
    reset_nonce_registry()
    t = _valid_token()
    r = verify_passport_token(t, expected_owner="SomeoneElse", require_signature=False)
    assert r.ok is False and r.stage == "owner_binding"
    r2 = verify_passport_token(
        _valid_token(nonce="owner-ok-nonce"),
        expected_owner="Appel420",
        require_signature=False,
    )
    assert r2.ok is True


def test_token_build_binding():
    reset_nonce_registry()
    t = _valid_token(nonce="build-bind-nonce")
    r = verify_passport_token(t, expected_build_id="missing-build", require_signature=False)
    assert r.ok is False and r.stage == "build_binding"
    r2 = verify_passport_token(
        _valid_token(nonce="build-ok-nonce"),
        expected_build_id="passport",
        require_signature=False,
    )
    assert r2.ok is True


def test_token_happy_path_no_sig_required():
    reset_nonce_registry()
    t = _valid_token(nonce="happy-path-nonce")
    r = verify_passport_token(t, require_signature=False)
    assert r.ok is True and r.stage == "complete"


def test_provenance_rejects_bad_version():
    rec = {
        "schema_version": "9.9",
        "record_id": "prv_1",
        "created_at": 1.0,
        "query": "q",
        "answer_hash": "a" * 16,
        "model": "m",
        "contributions": [{"creator_id": "x", "role": "author", "portion": 1.0}],
    }
    r = verify_provenance_record(rec)
    assert r.ok is False and r.stage == "version"


def test_provenance_portions_must_sum():
    rec = {
        "schema_version": "0.1.0",
        "record_id": "prv_1",
        "created_at": 1.0,
        "query": "q",
        "answer_hash": "a" * 16,
        "model": "m",
        "contributions": [
            {"creator_id": "x", "role": "author", "portion": 0.3},
            {"creator_id": "y", "role": "model", "portion": 0.3},
        ],
    }
    r = verify_provenance_record(rec)
    assert r.ok is False and r.stage == "contributions"


def test_provenance_answer_hash():
    import hashlib

    answer = "hello world"
    h = hashlib.sha256(answer.encode()).hexdigest()[:16]
    rec = {
        "schema_version": "0.1.0",
        "record_id": "prv_1",
        "created_at": 1.0,
        "query": "q",
        "answer_hash": h,
        "model": "m",
        "contributions": [{"creator_id": "Appel420", "role": "author", "portion": 1.0}],
        "opt_in": {},
    }
    r = verify_provenance_record(rec, expected_answer=answer)
    assert r.ok is True
    r2 = verify_provenance_record(rec, expected_answer="wrong")
    assert r2.ok is False and r2.stage == "answer_hash"


def test_provenance_rejects_legacy_opt_in_bool():
    rec = {
        "schema_version": "0.1.0",
        "record_id": "prv_1",
        "created_at": 1.0,
        "query": "q",
        "answer_hash": "a" * 16,
        "model": "m",
        "contributions": [{"creator_id": "x", "role": "author", "portion": 1.0}],
        "opt_in": {"x": True},
    }
    r = verify_provenance_record(rec)
    assert r.ok is False and r.stage == "opt_in"


def test_provenance_accepts_toggle_opt_in():
    rec = {
        "schema_version": "0.1.0",
        "record_id": "prv_1",
        "created_at": 1.0,
        "query": "q",
        "answer_hash": "a" * 16,
        "model": "m",
        "contributions": [{"creator_id": "Appel420", "role": "author", "portion": 1.0}],
        "opt_in": {"Appel420": default_opt_in()},
    }
    r = verify_provenance_record(rec, expected_creator="Appel420")
    assert r.ok is True


def test_default_opt_in_deny():
    d = default_opt_in()
    assert d == {"training": False, "remixing": False, "redistribution": False}


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"PASS  {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    sys.exit(1 if failed else 0)
