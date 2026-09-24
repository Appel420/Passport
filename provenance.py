# provenance.py
# CAPL – Creator Attribution & Provenance Layer (record)
# Zero dependencies. Deny-by-default friendly.

from __future__ import annotations

import json
import hashlib
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict


SCHEMA_VERSION = "0.1.0"


def default_opt_in() -> Dict[str, bool]:
    """Deny-by-default toggles: training, remixing, redistribution."""
    return {"training": False, "remixing": False, "redistribution": False}


@dataclass
class Source:
    kind: str                       # "web", "repo", "model", "human", "dataset", "work"
    ref: str                        # url, commit sha, model id, work_id, name
    accessed: Optional[float] = None
    license: Optional[str] = None
    weight: float = 1.0             # influence on the answer, 0..1


@dataclass
class Contribution:
    creator_id: str
    role: str                       # "author", "reviewer", "curator", "model"
    portion: float                  # 0..1, ideally sums to ~1 across contributions
    sources: List[Source] = field(default_factory=list)
    work_id: Optional[str] = None   # optional link into the opt-in registry


@dataclass
class ProvenanceRecord:
    schema_version: str
    record_id: str
    created_at: float
    query: str
    answer_hash: str
    model: str
    contributions: List[Contribution]
    citations: List[str] = field(default_factory=list)
    # creator_id -> {training, remixing, redistribution}; missing = all False
    opt_in: Dict[str, Dict[str, bool]] = field(default_factory=dict)
    parent_id: Optional[str] = None  # for remix chains

    def fingerprint(self) -> str:
        """Deterministic short hash over canonicalized JSON."""
        payload = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def to_json(self, path: Optional[str] = None) -> str:
        s = json.dumps(asdict(self), indent=2, ensure_ascii=False, default=str)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(s)
                f.write("\n")
        return s

    def set_opt_in(
        self,
        creator_id: str,
        *,
        training: bool = False,
        remixing: bool = False,
        redistribution: bool = False,
    ) -> None:
        self.opt_in[creator_id] = {
            "training": training,
            "remixing": remixing,
            "redistribution": redistribution,
        }


def make_record(
    query: str,
    answer: str,
    model: str,
    contributions: List[Contribution],
    citations: Optional[List[str]] = None,
    parent_id: Optional[str] = None,
    record_id: Optional[str] = None,
    opt_in: Optional[Dict[str, Dict[str, bool]]] = None,
) -> ProvenanceRecord:
    """Create a new provenance record. Uses time_ns() to avoid same-second collisions."""
    now_ns = time.time_ns()
    rec = ProvenanceRecord(
        schema_version=SCHEMA_VERSION,
        record_id=record_id or f"prv_{now_ns}",
        created_at=now_ns / 1_000_000_000,  # seconds as float
        query=query,
        answer_hash=hashlib.sha256(answer.encode("utf-8")).hexdigest()[:16],
        model=model,
        contributions=contributions,
        citations=citations or [],
        opt_in=opt_in or {},
        parent_id=parent_id,
    )
    return rec
