import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend import memory_service
from backend.apply import apply_decisions
from backend.db import get_db
from backend.decision import Decision, decide
from backend.formatter import format as format_text
from backend.retrieval import retrieve
from backend.schemas import (
    BulkObservePairResult,
    BulkObserveRequest,
    BulkObserveResponse,
    ConversationLearnedPair,
    ConversationResultOut,
    EvidenceOut,
    InterventionOut,
    LearnedPair,
    LearnFromConversationsRequest,
    LearnFromConversationsResponse,
    MemoryDetailOut,
    MemoryOut,
    ObserveRequest,
    ObserveResponse,
    ResetResponse,
    RunRequest,
    RunResponse,
)
from backend.tokenizer import tokenize

router = APIRouter()


@router.get("/health")
def health(session: Session = Depends(get_db)):
    session.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}


def _decision_to_intervention_out(d: Decision) -> InterventionOut:
    return InterventionOut(
        span=d.span_text,
        applied=d.canonical_form,
        memory_id=d.memory_id,
        observed_form=d.observed_form,
        entity_type=d.entity_type or "other",
        match_type=d.match_type or "exact",
        edit_distance=d.edit_distance if d.edit_distance is not None else 0,
        confidence=d.confidence if d.confidence is not None else 0.0,
        evidence_count=d.evidence_count if d.evidence_count is not None else 0,
        reason=d.reason,
        explanation=d.explanation,
    )


def run_transcript(session: Session, asr: str) -> RunResponse:
    start = time.perf_counter()

    formatted = format_text(asr)
    tokens = tokenize(formatted)
    candidates = retrieve(session, tokens)
    decisions = decide(tokens, candidates, formatted)
    memory_aware = apply_decisions(formatted, tokens, decisions)

    interventions = [_decision_to_intervention_out(d) for d in decisions if d.kind == "intervene"]
    non_interventions = [_decision_to_intervention_out(d) for d in decisions if d.kind == "no_intervene"]

    latency_ms = (time.perf_counter() - start) * 1000

    return RunResponse(
        asr=asr,
        formatted=formatted,
        memory_aware=memory_aware,
        interventions=interventions,
        non_interventions=non_interventions,
        latency_ms=round(latency_ms, 3),
    )


@router.post("/observe", response_model=ObserveResponse, status_code=201)
def observe(req: ObserveRequest, session: Session = Depends(get_db)):
    if not req.asr.strip() or not req.corrected.strip():
        raise HTTPException(status_code=400, detail="'asr' and 'corrected' must be non-empty")

    results, formatted = memory_service.learn(session, req.asr, req.corrected)
    learned = [
        LearnedPair(
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
    return ObserveResponse(formatted_baseline=formatted, learned=learned)


@router.post("/observe/bulk", response_model=BulkObserveResponse, status_code=201)
def observe_bulk(req: BulkObserveRequest, session: Session = Depends(get_db)):
    if not req.observations:
        raise HTTPException(status_code=400, detail="'observations' must be non-empty")

    pairs = [(o.asr, o.corrected) for o in req.observations]
    bulk_results = memory_service.learn_bulk_pairs(session, pairs)
    results = [
        BulkObservePairResult(
            pair_index=br.pair_index,
            formatted_baseline=br.formatted_baseline,
            learned=[
                LearnedPair(
                    observed_form=l.observed_form,
                    canonical_form=l.canonical_form,
                    memory_id=l.memory_id,
                    evidence_count=l.evidence_count,
                    confidence=l.confidence,
                    active=l.active,
                    status=l.status,
                )
                for l in br.learned
            ],
            error=br.error,
        )
        for br in bulk_results
    ]
    return BulkObserveResponse(results=results)


@router.post("/learn-from-conversations", response_model=LearnFromConversationsResponse)
def learn_from_conversations(req: LearnFromConversationsRequest, session: Session = Depends(get_db)):
    if not req.conversations:
        raise HTTPException(status_code=400, detail="'conversations' must be non-empty")

    # No credentials try/except here - learn_from_conversations already treats
    # a missing LLM key as normal (NER's free pass still runs).
    results = memory_service.learn_from_conversations(session, req.conversations)

    return LearnFromConversationsResponse(
        results=[
            ConversationResultOut(
                conversation_index=r.conversation_index,
                learned=[
                    ConversationLearnedPair(
                        entity_text=l.entity_text,
                        observed_form=l.observed_form,
                        canonical_form=l.canonical_form,
                        entity_type=l.entity_type,
                        memory_id=l.memory_id,
                        evidence_count=l.evidence_count,
                        confidence=l.confidence,
                        active=l.active,
                        status=l.status,
                        sources=l.sources,
                    )
                    for l in r.learned
                ],
                error=r.error,
            )
            for r in results
        ]
    )


@router.get("/memories", response_model=list[MemoryOut])
def get_memories(active_only: bool = False, session: Session = Depends(get_db)):
    rows = memory_service.list_memories(session, active_only=active_only)
    return [MemoryOut(**r.to_dict()) for r in rows]


@router.get("/memories/{memory_id}", response_model=MemoryDetailOut)
def get_memory_detail(memory_id: int, session: Session = Depends(get_db)):
    row = memory_service.get_memory(session, memory_id)
    if row is None:
        raise HTTPException(status_code=404, detail="memory not found")
    evidence = memory_service.get_evidence_for(session, memory_id)
    return MemoryDetailOut(
        memory=MemoryOut(**row.to_dict()),
        evidence=[EvidenceOut(**e.to_dict()) for e in evidence],
    )


@router.delete("/memories/{memory_id}", status_code=204)
def delete_memory(memory_id: int, session: Session = Depends(get_db)):
    ok = memory_service.delete_memory(session, memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="memory not found")
    return None


@router.post("/run", response_model=RunResponse)
def run(req: RunRequest, session: Session = Depends(get_db)):
    if not req.asr.strip():
        raise HTTPException(status_code=400, detail="'asr' must be non-empty")
    return run_transcript(session, req.asr)


@router.post("/reset", response_model=ResetResponse)
def reset(session: Session = Depends(get_db)):
    counts = memory_service.reset_all(session)
    return ResetResponse(status="reset", **counts)
