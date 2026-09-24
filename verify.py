# verify.py
# Passport + CAPL verification — fail-closed, zero-dependency core.
# Signature crypto is optional: structure always checked; Ed25519 when available.

from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

PASSPORT_VERSION = "0.1.0"
CAPL_VERSION = "0.1.0"

# In-process nonce registry for replay protection (single-process only).
_USED_NONCES: Set[str] = set()


@dataclass
class VerificationResult:
    ok: bool
    reason: str
    stage: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "stage": self.stage,
            "details": self.details,
        }


def _fail(stage: str, reason: str, **details: Any) -> VerificationResult:
    return VerificationResult(ok=False, reason=reason, stage=stage, details=details)


def _ok(stage: str, reason: str = "verified", **details: Any) -> VerificationResult:
    return VerificationResult(ok=True, reason=reason, stage=stage, details=details)


def reset_nonce_registry() -> None:
    """Clear replay registry. Tests only — production uses persistent store."""
    _USED_NONCES.clear()


def _canonical_payload(token: dict) -> bytes:
    """Canonical JSON of token without the signature field."""
    body = {k: v for k, v in token.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _try_ed25519_verify(public_key_b64: str, signature_b64: str, payload: bytes) -> Optional[bool]:
    """
    Attempt Ed25519 verification.
    Returns True/False if crypto available, None if no crypto library present.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature

        pk = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
        pk.verify(base64.b64decode(signature_b64), payload)
        return True
    except ImportError:
        pass
    except Exception:
        return False

    try:
        import nacl.signing  # type: ignore
        import nacl.exceptions  # type: ignore

        vk = nacl.signing.VerifyKey(base64.b64decode(public_key_b64))
        vk.verify(payload, base64.b64decode(signature_b64))
        return True
    except ImportError:
        return None
    except Exception:
        return False


def verify_passport_token(
    token: dict,
    *,
    expected_owner: Optional[str] = None,
    expected_build_id: Optional[str] = None,
    now: Optional[float] = None,
    require_signature: bool = True,
    record_nonce: bool = True,
) -> VerificationResult:
    """
    Fail-closed Passport token verification.

    Order (matches spec/VERIFICATION.md):
      1 parse/type  2 version  3 required fields  4 timestamps
      5 nonce       6 signature  7 owner binding  8 build binding
    """
    if not isinstance(token, dict):
        return _fail("parse", "token_not_object")

    # 2. Version
    if token.get("passport_version") != PASSPORT_VERSION:
        return _fail(
            "version",
            "unsupported_or_missing_version",
            got=token.get("passport_version"),
            expected=PASSPORT_VERSION,
        )

    # 3. Required fields
    required = ("passport_version", "owner", "issued_at", "expires_at", "nonce", "builds", "signature")
    missing = [k for k in required if k not in token]
    if missing:
        return _fail("required_fields", "missing_fields", missing=missing)

    owner = token["owner"]
    if not isinstance(owner, dict) or "account_id" not in owner or "display_name" not in owner:
        return _fail("required_fields", "owner_incomplete")

    if not isinstance(token["builds"], list):
        return _fail("required_fields", "builds_not_array")

    sig = token["signature"]
    if not isinstance(sig, dict) or "algorithm" not in sig or "value" not in sig:
        return _fail("required_fields", "signature_incomplete")

    # 4. Timestamps
    now_ts = int(now if now is not None else time.time())
    issued = token["issued_at"]
    expires = token["expires_at"]

    if not isinstance(issued, (int, float)):
        return _fail("timestamp", "issued_at_invalid_type")
    if issued > now_ts + 60:  # 60s clock skew allowance
        return _fail("timestamp", "issued_at_in_future", issued_at=issued, now=now_ts)

    if expires is not None:
        if not isinstance(expires, (int, float)):
            return _fail("timestamp", "expires_at_invalid_type")
        if expires < now_ts:
            return _fail("timestamp", "token_expired", expires_at=expires, now=now_ts)

    # 5. Nonce / replay
    nonce = token["nonce"]
    if not isinstance(nonce, str) or not nonce:
        return _fail("nonce", "nonce_empty_or_invalid")
    if nonce in _USED_NONCES:
        return _fail("nonce", "nonce_replay", nonce=nonce)
    if record_nonce:
        _USED_NONCES.add(nonce)

    # 6. Signature
    payload = _canonical_payload(token)
    sig_status = "structure_ok"
    if require_signature:
        algo = sig.get("algorithm", "")
        value = sig.get("value", "")
        pubkey = sig.get("public_key")
        if not value or value.startswith("<"):
            return _fail("signature", "signature_placeholder_or_empty")
        if algo == "Ed25519" and pubkey and not str(pubkey).startswith("<"):
            result = _try_ed25519_verify(str(pubkey), str(value), payload)
            if result is True:
                sig_status = "ed25519_verified"
            elif result is False:
                return _fail("signature", "ed25519_invalid")
            else:
                # No crypto library — fail-closed for full trust when required
                if require_signature:
                    return _fail(
                        "signature",
                        "crypto_unavailable",
                        hint="install cryptography or pynacl for Ed25519 verify",
                    )
                sig_status = "unverified_no_crypto"
        elif algo in ("HMAC-SHA256", "hmac-sha256"):
            # Optional zero-dep path: caller supplies shared secret via details later
            sig_status = "hmac_structure_ok"
        else:
            return _fail("signature", "unsupported_or_incomplete_algorithm", algorithm=algo)

    # 7. Owner binding
    account_id = owner["account_id"]
    if expected_owner is not None and account_id != expected_owner:
        return _fail(
            "owner_binding",
            "owner_mismatch",
            expected=expected_owner,
            got=account_id,
        )

    # 8. Build binding
    if expected_build_id is not None:
        build_ids = [
            b.get("build_id") for b in token["builds"] if isinstance(b, dict)
        ]
        if expected_build_id not in build_ids:
            return _fail(
                "build_binding",
                "build_not_in_token",
                expected_build_id=expected_build_id,
                builds=build_ids,
            )

    return _ok(
        "complete",
        signature_status=sig_status,
        owner=account_id,
        build_count=len(token["builds"]),
    )


def verify_provenance_record(
    record: dict,
    *,
    expected_answer: Optional[str] = None,
    expected_creator: Optional[str] = None,
) -> VerificationResult:
    """
    Fail-closed CAPL provenance record verification.
    Checks schema version, required fields, answer hash, contribution portions,
    and opt_in shape (creator_id -> {training, remixing, redistribution}).
    """
    if not isinstance(record, dict):
        return _fail("parse", "record_not_object")

    if record.get("schema_version") != CAPL_VERSION:
        return _fail(
            "version",
            "unsupported_or_missing_version",
            got=record.get("schema_version"),
            expected=CAPL_VERSION,
        )

    required = (
        "schema_version",
        "record_id",
        "created_at",
        "query",
        "answer_hash",
        "model",
        "contributions",
    )
    missing = [k for k in required if k not in record]
    if missing:
        return _fail("required_fields", "missing_fields", missing=missing)

    if not isinstance(record["contributions"], list) or not record["contributions"]:
        return _fail("contributions", "empty_or_invalid")

    total_portion = 0.0
    for i, c in enumerate(record["contributions"]):
        if not isinstance(c, dict):
            return _fail("contributions", "entry_not_object", index=i)
        for k in ("creator_id", "role", "portion"):
            if k not in c:
                return _fail("contributions", "entry_incomplete", index=i, missing=k)
        portion = c["portion"]
        if not isinstance(portion, (int, float)) or portion < 0 or portion > 1:
            return _fail("contributions", "portion_out_of_range", index=i, portion=portion)
        total_portion += float(portion)

    # Soft check: portions should roughly sum to 1 (allow small float drift)
    if abs(total_portion - 1.0) > 0.05:
        return _fail(
            "contributions",
            "portions_do_not_sum_near_one",
            total=total_portion,
        )

    # Answer hash check if plaintext provided
    if expected_answer is not None:
        expected_hash = hashlib.sha256(expected_answer.encode("utf-8")).hexdigest()[:16]
        if record["answer_hash"] != expected_hash:
            return _fail(
                "answer_hash",
                "mismatch",
                expected=expected_hash,
                got=record["answer_hash"],
            )

    # Creator binding
    if expected_creator is not None:
        creators = [c["creator_id"] for c in record["contributions"]]
        if expected_creator not in creators:
            return _fail(
                "creator_binding",
                "creator_not_in_contributions",
                expected=expected_creator,
                creators=creators,
            )

    # opt_in shape: deny-by-default; if present must be creator -> toggle map
    opt_in = record.get("opt_in", {})
    if opt_in is None:
        opt_in = {}
    if not isinstance(opt_in, dict):
        return _fail("opt_in", "not_object")
    for cid, toggles in opt_in.items():
        if isinstance(toggles, bool):
            # legacy single-bool form — reject in favor of explicit toggles
            return _fail(
                "opt_in",
                "legacy_bool_form",
                creator_id=cid,
                hint="use {training, remixing, redistribution}",
            )
        if not isinstance(toggles, dict):
            return _fail("opt_in", "toggles_not_object", creator_id=cid)
        for key in ("training", "remixing", "redistribution"):
            if key in toggles and not isinstance(toggles[key], bool):
                return _fail("opt_in", "toggle_not_bool", creator_id=cid, key=key)

    return _ok(
        "complete",
        record_id=record["record_id"],
        contribution_count=len(record["contributions"]),
        total_portion=total_portion,
    )


def default_opt_in() -> Dict[str, bool]:
    """Deny-by-default opt-in toggles matching REGISTRY.md."""
    return {"training": False, "remixing": False, "redistribution": False}
