"""Idempotent database initializer. Safe to run any number of times.

This doubles as the project's "migration": since the schema has exactly
one version for this assignment's scope, a full Alembic setup would be
overkill. Re-running this script never drops or alters existing data.

Usage:
    python scripts/init_db.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config
from backend.db import get_engine
from backend.models import Base


def init_db(db_path: str | None = None) -> None:
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    print(f"Database ready at: {db_path or config.DB_PATH}")


if __name__ == "__main__":
    init_db()
