from pydantic import BaseModel


class ObserveRequest(BaseModel):
    asr: str
    corrected: str


class LearnedPair(BaseModel):
    observed_form: str
    canonical_form: str
    memory_id: int
    evidence_count: int
    confidence: float
    active: bool
    status: str


class ObserveResponse(BaseModel):
    formatted_baseline: str
    learned: list[LearnedPair]


class BulkObserveRequest(BaseModel):
    observations: list[ObserveRequest]


class BulkObservePairResult(BaseModel):
    pair_index: int
    formatted_baseline: str | None
    learned: list[LearnedPair]
    error: str | None = None


class BulkObserveResponse(BaseModel):
    results: list[BulkObservePairResult]


class LearnFromConversationsRequest(BaseModel):
    conversations: list[str]


class ConversationLearnedPair(BaseModel):
    entity_text: str
    observed_form: str
    canonical_form: str
    entity_type: str
    memory_id: int
    evidence_count: int
    confidence: float
    active: bool
    status: str
    sources: list[str]


class ConversationResultOut(BaseModel):
    conversation_index: int
    learned: list[ConversationLearnedPair]
    error: str | None = None


class LearnFromConversationsResponse(BaseModel):
    results: list[ConversationResultOut]


class MemoryOut(BaseModel):
    id: int
    observed_form: str
    canonical_form: str
    entity_type: str
    token_count: int
    evidence_count: int
    confidence: float
    active: bool
    created_at: str
    last_updated: str


class EvidenceOut(BaseModel):
    id: int
    memory_id: int | None
    observed_form: str
    canonical_form: str
    source_asr: str | None
    source_corrected: str
    source_type: str
    created_at: str


class MemoryDetailOut(BaseModel):
    memory: MemoryOut
    evidence: list[EvidenceOut]


class RunRequest(BaseModel):
    asr: str


class InterventionOut(BaseModel):
    span: str
    applied: str | None
    memory_id: int
    observed_form: str
    entity_type: str
    match_type: str
    edit_distance: int
    confidence: float
    evidence_count: int
    reason: str
    explanation: str


class RunResponse(BaseModel):
    asr: str
    formatted: str
    memory_aware: str
    interventions: list[InterventionOut]
    non_interventions: list[InterventionOut]
    latency_ms: float


class ResetResponse(BaseModel):
    status: str
    memories_deleted: int
    evidence_deleted: int
