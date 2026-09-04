"""Load reproducible seed data into the demo database.

Idempotent-ish: re-running just reinforces the same memories further (their
evidence_count/confidence keeps climbing, which is harmless - it does not
create duplicates because memory_service.learn() matches on
(observed_form, canonical_form)).

Usage:
    python scripts/seed.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import memory_service
from backend.db import get_session
from backend.models import Base
from backend.db import get_engine

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_observations.jsonl"


def seed() -> None:
    Base.metadata.create_all(get_engine())
    session = get_session()
    try:
        lines = [
            json.loads(line) for line in SEED_FILE.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        for obs in lines:
            memory_service.learn(session, obs["asr"], obs["corrected"])
        rows = memory_service.list_memories(session)
        print(f"Seeded {len(lines)} observations -> {len(rows)} memory entries:")
        for r in rows:
            status = "active" if r.active else "candidate"
            print(f"  {r.observed_form!r} -> {r.canonical_form!r} [{status}, {r.evidence_count} obs]")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
