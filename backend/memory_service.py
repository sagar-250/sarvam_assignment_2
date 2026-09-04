"""Memory lifecycle: learning from observations, listing, deleting, resetting.

Confidence = min(1.0, evidence_count / EVIDENCE_THRESHOLD). With the default
EVIDENCE_THRESHOLD=3 and MIN_EVIDENCE_ACTIVE=2, confidence crosses
MIN_CONFIDENCE_ACTIVE=0.6 (0.667) at exactly the same point evidence_count
crosses 2 - the two thresholds never disagree.

A single observation is deliberately NOT enough to change output: it could be
a one-off ASR fluke or a user typo. A second, independent confirmation of the
same correction is required before the memory is trusted (see README).
"""
from dataclasses import dataclass

from sqlalchemy import delete as sa_delete
from sqlalchemy.orm import Session

from backend import config
from backend.diff import ObservationPair, extract_observations
from backend.grouping import maybe_group_adjacent_pairs
from backend.models import Evidence, Memory


@dataclass
class LearnResult:
    memory: Memory
    pair: ObservationPair
    status: str  # "new_candidate" | "reinforced" | "activated" | "already_active"


def _compute_active(evidence_count: int, confidence: float) -> bool:
    return evidence_count >= config.MIN_EVIDENCE_ACTIVE and confidence >= config.MIN_CONFIDENCE_ACTIVE


def _upsert_memory(
    session: Session, observed_form: str, canonical_form: str, entity_type: str, token_count: int
) -> tuple[Memory, str]:
    """Upsert one Memory row keyed by (observed_form, canonical_form) and
    recompute evidence_count/confidence/active. Caller owns the Evidence row
    and the commit. Shared by learn() (word-level diff pairs) and
    learn_from_conversations() (extracted entities) so the activation math
    lives in exactly one place."""
    row = (
        session.query(Memory)
        .filter(Memory.observed_form == observed_form, Memory.canonical_form == canonical_form)
        .one_or_none()
    )
    was_active = bool(row.active) if row else False

    if row is None:
        row = Memory(
            observed_form=observed_form,
            canonical_form=canonical_form,
            entity_type=entity_type,
            token_count=token_count,
            evidence_count=1,
            confidence=round(min(1.0, 1 / config.EVIDENCE_THRESHOLD), 3),
            active=False,
        )
        row.active = _compute_active(row.evidence_count, row.confidence)
        session.add(row)
        session.flush()
        return row, "new_candidate"

    row.evidence_count += 1
    row.confidence = round(min(1.0, row.evidence_count / config.EVIDENCE_THRESHOLD), 3)
    row.active = _compute_active(row.evidence_count, row.confidence)
    status = "already_active" if was_active else ("activated" if row.active else "reinforced")
    return row, status


def learn(session: Session, asr: str, corrected: str) -> tuple[list[LearnResult], str]:
    pairs, formatted = extract_observations(asr, corrected)
    pairs, _ = maybe_group_adjacent_pairs(pairs, corrected)
    results: list[LearnResult] = []

    for pair in pairs:
        row, status = _upsert_memory(session, pair.observed_form, pair.canonical_form, pair.entity_type, pair.token_count)
        session.add(
            Evidence(
                memory_id=row.id,
                observed_form=pair.observed_form,
                canonical_form=pair.canonical_form,
                source_asr=asr,
                source_corrected=corrected,
            )
        )
        results.append(LearnResult(memory=row, pair=pair, status=status))

    session.commit()
    return results, formatted


@dataclass
class BulkPairLearnedItem:
    observed_form: str
    canonical_form: str
    memory_id: int
    evidence_count: int
    confidence: float
    active: bool
    status: str


@dataclass
class BulkPairResult:
    pair_index: int
    formatted_baseline: str | None
    learned: list[BulkPairLearnedItem]
    error: str | None = None


def learn_bulk_pairs(session: Session, pairs: list[tuple[str, str]]) -> list[BulkPairResult]:
    """Teach many (asr, corrected) pairs at once - a thin loop over learn(),
    reusing its exact upsert/evidence/activation logic unchanged. Each pair is
    validated independently so one malformed row doesn't abort the batch.

    Snapshots evidence_count/confidence/active into plain values right after
    each learn() call rather than holding onto the live LearnResult - if a
    later pair in the same batch reinforces the same Memory row, SQLAlchemy's
    identity map means every earlier LearnResult.memory for that row is the
    SAME mutable object, so deferring the read would silently report every
    pair's state as whatever the row ended up at by the end of the loop."""
    out: list[BulkPairResult] = []
    for idx, (asr, corrected) in enumerate(pairs):
        if not asr.strip() or not corrected.strip():
            out.append(
                BulkPairResult(
                    pair_index=idx, formatted_baseline=None, learned=[],
                    error="'asr' and 'corrected' must be non-empty",
                )
            )
            continue
        results, formatted = learn(session, asr, corrected)
        learned = [
            BulkPairLearnedItem(
                observed_form=r.pair.observed_form,
                canonical_form=r.pair.canonical_form,
                memory_id=r.memory.id,
                evidence_count=r.memory.evidence_count,
                confidence=r.memory.confidence,
                active=r.memory.active,
                status=r.status,
            )
            for r in results
        ]
        out.append(BulkPairResult(pair_index=idx, formatted_baseline=formatted, learned=learned))
    return out


@dataclass
class ConversationLearnedItem:
    entity_text: str
    observed_form: str
    canonical_form: str
    entity_type: str
    memory_id: int
    evidence_count: int
    confidence: float
    active: bool
    status: str
    sources: list[str]  # ["ner"], ["llm"], or ["ner", "llm"] if both agreed


@dataclass
class ConversationResult:
    conversation_index: int
    learned: list[ConversationLearnedItem]
    error: str | None = None


def learn_from_conversations(session: Session, conversation_texts: list[str]) -> list[ConversationResult]:
    """Teach Kivi from finished, already-corrected conversation transcripts -
    no raw-ASR side needed, so backend.diff's (wrong, right) pair diffing
    can't apply. Two extraction passes feed the same _upsert_memory()/
    evidence/activation logic learn() uses:

    1. backend.ner_extraction - spaCy NER, free, offline, always attempted.
       Real but imperfect: strong on ordinary names/places, weak on the
       idiosyncratic/invented terms this system exists to remember (verified
       directly - see that module's docstring).
    2. backend.entity_extraction - LLM-based, optional. Attempted only if
       provider credentials are configured; a missing key is treated as
       "this pass didn't run," not an error - the whole feature must never
       be worse than NER alone just because no LLM key is set. Any OTHER
       failure (malformed output, network error after internal retries) is
       swallowed the same way, for the same reason: a transient LLM hiccup
       shouldn't discard entities NER already found.

    Results are merged by normalized form; when both passes find the same
    entity, the LLM's classification wins (more context to work with) and
    `sources` records both. Entities are deduplicated WITHIN each
    conversation before upserting, so a name mentioned 5 times in one
    document contributes at most 1 evidence increment - a single document
    shouldn't be able to fake independent multi-source confirmation."""
    from backend.entity_extraction import extract_entities
    from backend.llm_client import LLMCredentialsMissingError
    from backend.ner_extraction import extract_entities_ner, ner_model_available
    from backend.tokenizer import normalize_span
    # Local imports: keeps this module importable, and the NER-only path
    # fully usable, even when entity_extraction's LLM dependency chain
    # (backend.llm_client) is never exercised - the optional-feature
    # boundary the rest of this file otherwise has no reason to know about.

    out: list[ConversationResult] = []
    for idx, convo in enumerate(conversation_texts):
        if not convo.strip():
            out.append(ConversationResult(conversation_index=idx, learned=[], error="conversation text must be non-empty"))
            continue

        ner_entities = extract_entities_ner(convo)

        llm_entities: list = []
        llm_attempted = False
        try:
            llm_entities = extract_entities(convo)
            llm_attempted = True
        except LLMCredentialsMissingError:
            pass  # normal, expected when no key is configured - not a failure
        except Exception:  # noqa: BLE001 - never let a transient LLM failure discard NER's results
            pass

        if not ner_entities and not llm_entities:
            error = None
            if not ner_model_available() and not llm_attempted:
                error = (
                    "No extraction mechanism available: the spaCy NER model isn't installed "
                    "(python -m spacy download en_core_web_sm) and no LLM credentials are configured."
                )
            out.append(ConversationResult(conversation_index=idx, learned=[], error=error))
            continue

        # observed_form -> (entity_text, canonical_form, entity_type, token_count, sources)
        merged: dict[str, tuple[str, str, str, int, set[str]]] = {}
        for source, entities in (("ner", ner_entities), ("llm", llm_entities)):
            for e in entities:
                span = normalize_span(e.entity_text)
                if span is None:
                    continue
                observed_form, canonical_form, token_count = span
                if token_count > config.MAX_SPAN_TOKENS:
                    continue
                if observed_form in merged:
                    prev_text, prev_canonical, prev_type, prev_count, prev_sources = merged[observed_form]
                    # LLM's classification wins on overlap - more context to work with.
                    entity_type = e.entity_type if source == "llm" else prev_type
                    merged[observed_form] = (prev_text, prev_canonical, entity_type, prev_count, prev_sources | {source})
                else:
                    merged[observed_form] = (e.entity_text, canonical_form, e.entity_type, token_count, {source})

        learned: list[ConversationLearnedItem] = []
        for observed_form, (entity_text, canonical_form, entity_type, token_count, sources) in merged.items():
            row, status = _upsert_memory(session, observed_form, canonical_form, entity_type, token_count)
            session.add(
                Evidence(
                    memory_id=row.id,
                    observed_form=observed_form,
                    canonical_form=canonical_form,
                    source_asr=None,
                    source_corrected=convo,
                    source_type="conversation_extraction",
                )
            )
            learned.append(
                ConversationLearnedItem(
                    entity_text=entity_text,
                    observed_form=observed_form,
                    canonical_form=canonical_form,
                    entity_type=row.entity_type,
                    memory_id=row.id,
                    evidence_count=row.evidence_count,
                    confidence=row.confidence,
                    active=row.active,
                    status=status,
                    sources=sorted(sources),
                )
            )
        out.append(ConversationResult(conversation_index=idx, learned=learned))

    session.commit()
    return out


def list_memories(session: Session, active_only: bool = False) -> list[Memory]:
    q = session.query(Memory)
    if active_only:
        q = q.filter(Memory.active.is_(True))
    return q.order_by(Memory.active.desc(), Memory.last_updated.desc()).all()


def get_memory(session: Session, memory_id: int) -> Memory | None:
    return session.get(Memory, memory_id)


def get_evidence_for(session: Session, memory_id: int) -> list[Evidence]:
    return (
        session.query(Evidence)
        .filter(Evidence.memory_id == memory_id)
        .order_by(Evidence.created_at.asc())
        .all()
    )


def delete_memory(session: Session, memory_id: int) -> bool:
    row = session.get(Memory, memory_id)
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True


def reset_all(session: Session) -> dict:
    evidence_count = session.query(Evidence).count()
    memory_count = session.query(Memory).count()
    session.execute(sa_delete(Evidence))
    session.execute(sa_delete(Memory))
    session.commit()
    return {"memories_deleted": memory_count, "evidence_deleted": evidence_count}
