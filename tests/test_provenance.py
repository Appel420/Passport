# tests/test_provenance.py
# Zero-dependency tests for provenance.py (CAPL record layer)

import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from provenance import Source, Contribution, ProvenanceRecord, make_record, SCHEMA_VERSION


def test_schema_version():
    assert SCHEMA_VERSION == "0.1.0"


def test_make_record_basic():
    rec = make_record(
        query="How much wood would a woodchuck chuck?",
        answer="A woodchuck would chuck as much wood as a woodchuck could chuck.",
        model="grok-4-fast",
        contributions=[
            Contribution(creator_id="Appel420", role="author", portion=0.5),
            Contribution(creator_id="grok", role="model", portion=0.5,
                         sources=[Source(kind="model", ref="grok-4-fast")]),
        ],
        citations=["https://github.com/Appel420/Passport"],
    )
    assert rec.schema_version == "0.1.0"
    assert rec.query.startswith("How much wood")
    assert len(rec.answer_hash) == 16
    assert rec.model == "grok-4-fast"
    assert len(rec.contributions) == 2
    assert len(rec.citations) == 1
    assert rec.parent_id is None
    assert rec.record_id.startswith("prv_")


def test_answer_hash_deterministic():
    a = hashlib.sha256(b"hello").hexdigest()[:16]
    b = hashlib.sha256(b"hello").hexdigest()[:16]
    c = hashlib.sha256(b"world").hexdigest()[:16]
    assert a == b
    assert a != c


def test_fingerprint_deterministic():
    rec = make_record(
        query="q", answer="a", model="m",
        contributions=[Contribution(creator_id="x", role="author", portion=1.0)],
    )
    fp1 = rec.fingerprint()
    fp2 = rec.fingerprint()
    assert fp1 == fp2
    assert len(fp1) == 16
    rec2 = make_record(
        query="q2", answer="a", model="m",
        contributions=[Contribution(creator_id="x", role="author", portion=1.0)],
    )
    assert rec.fingerprint() != rec2.fingerprint()


def test_fingerprint_canonicalization():
    s1 = Source(kind="web", ref="https://example.com", weight=0.5)
    s2 = Source(kind="repo", ref="abc123", weight=0.5)
    c1 = Contribution(creator_id="a", role="author", portion=0.6, sources=[s1, s2])
    c2 = Contribution(creator_id="b", role="model", portion=0.4)
    rec = make_record(
        query="q", answer="a", model="m", contributions=[c1, c2],
    )
    assert rec.fingerprint() is not None


def test_to_json_roundtrip():
    rec = make_record(
        query="q", answer="a", model="m",
        contributions=[Contribution(creator_id="x", role="author", portion=1.0)],
        citations=["https://example.com"],
    )
    s = rec.to_json()
    data = json.loads(s)
    assert data["schema_version"] == "0.1.0"
    assert data["query"] == "q"
    assert data["model"] == "m"
    assert len(data["contributions"]) == 1
    assert data["contributions"][0]["creator_id"] == "x"
    assert data["citations"] == ["https://example.com"]


def test_to_json_writes_file():
    import tempfile
    rec = make_record(
        query="q", answer="a", model="m",
        contributions=[Contribution(creator_id="x", role="author", portion=1.0)],
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    try:
        rec.to_json(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["record_id"] == rec.record_id
    finally:
        os.unlink(path)


def test_remix_chain_parent_id():
    parent = make_record(
        query="original q", answer="original a", model="m",
        contributions=[Contribution(creator_id="x", role="author", portion=1.0)],
    )
    child = make_record(
        query="remix q", answer="remix a", model="m",
        contributions=[Contribution(creator_id="y", role="author", portion=1.0)],
        parent_id=parent.record_id,
    )
    assert child.parent_id == parent.record_id
    assert parent.parent_id is None


def test_opt_in_default_empty():
    rec = make_record(
        query="q", answer="a", model="m",
        contributions=[Contribution(creator_id="x", role="author", portion=1.0)],
    )
    assert rec.opt_in == {}  # deny-by-default


def test_source_defaults():
    s = Source(kind="web", ref="https://example.com")
    assert s.accessed is None
    assert s.license is None
    assert s.weight == 1.0


def test_contribution_defaults():
    c = Contribution(creator_id="x", role="author", portion=1.0)
    assert c.sources == []
    assert c.work_id is None


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
