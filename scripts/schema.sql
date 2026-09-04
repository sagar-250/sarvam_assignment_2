-- Kivi phonetic memory system - schema DDL (mirrors backend/models.py)
-- Generated for human inspection; the authoritative source is backend/models.py,
-- applied via `python scripts/init_db.py` (SQLAlchemy Base.metadata.create_all).

CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_form VARCHAR NOT NULL,
    canonical_form VARCHAR NOT NULL,
    entity_type VARCHAR NOT NULL DEFAULT 'other',
    token_count INTEGER NOT NULL DEFAULT 1,
    evidence_count INTEGER NOT NULL DEFAULT 1,
    confidence FLOAT NOT NULL DEFAULT 0.0,
    active BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    last_updated DATETIME NOT NULL,
    CONSTRAINT ux_memory_observed_canonical UNIQUE (observed_form, canonical_form)
);

CREATE INDEX IF NOT EXISTS ix_memory_observed_form ON memory (observed_form);
CREATE INDEX IF NOT EXISTS ix_memory_active ON memory (active);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER,
    observed_form VARCHAR NOT NULL,
    canonical_form VARCHAR NOT NULL,
    source_asr TEXT,
    source_corrected TEXT NOT NULL,
    source_type VARCHAR NOT NULL DEFAULT 'observed_pair',
    created_at DATETIME NOT NULL,
    FOREIGN KEY (memory_id) REFERENCES memory (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_evidence_memory_id ON evidence (memory_id);
