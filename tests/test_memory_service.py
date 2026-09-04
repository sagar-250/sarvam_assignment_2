from unittest.mock import patch

from backend import entity_extraction, memory_service


def test_single_observation_stays_candidate(session):
    results, _ = memory_service.learn(session, "call aditya now", "Call Aaditya now")
    assert len(results) == 1
    r = results[0]
    assert r.memory.evidence_count == 1
    assert r.memory.active is False
    assert r.status == "new_candidate"


def test_second_agreeing_observation_activates(session):
    memory_service.learn(session, "call aditya now", "Call Aaditya now")
    results, _ = memory_service.learn(session, "call aditya now", "Call Aaditya now")
    r = results[0]
    assert r.memory.evidence_count == 2
    assert r.memory.active is True
    assert r.status == "activated"
    assert r.memory.confidence >= 0.6


def test_third_observation_saturates_confidence(session):
    for _ in range(3):
        results, _ = memory_service.learn(session, "call aditya now", "Call Aaditya now")
    assert results[0].memory.confidence == 1.0
    assert results[0].status == "already_active"


def test_reset_clears_everything(session):
    memory_service.learn(session, "call aditya now", "Call Aaditya now")
    counts = memory_service.reset_all(session)
    assert counts["memories_deleted"] == 1
    assert memory_service.list_memories(session) == []


def test_delete_memory(session):
    results, _ = memory_service.learn(session, "call aditya now", "Call Aaditya now")
    mem_id = results[0].memory.id
    assert memory_service.delete_memory(session, mem_id) is True
    assert memory_service.get_memory(session, mem_id) is None
    assert memory_service.delete_memory(session, mem_id) is False


def _mock_extract(entities):
    """entities: list of (entity_text, entity_type) - source text is derived
    so _valid()'s substring check passes without needing a real LLM."""
    return lambda text: [
        entity_extraction.ExtractedEntity(entity_text=t, entity_type=ty) for t, ty in entities
    ]


def test_conversation_mention_repeated_in_one_document_counts_once(session):
    convo = "Aaditya joined the call. Aaditya asked a question. Later Aaditya left."
    with patch.object(entity_extraction, "extract_entities", _mock_extract([("Aaditya", "person")] * 3)):
        results = memory_service.learn_from_conversations(session, [convo])
    assert len(results) == 1
    assert len(results[0].learned) == 1
    assert results[0].learned[0].evidence_count == 1
    assert results[0].learned[0].active is False
    assert results[0].learned[0].status == "new_candidate"


def test_conversation_entity_activates_on_second_distinct_conversation(session):
    convo_a = "Meet Aaditya tomorrow."
    convo_b = "Aaditya confirmed the meeting."
    with patch.object(entity_extraction, "extract_entities",_mock_extract([("Aaditya", "person")])):
        results = memory_service.learn_from_conversations(session, [convo_a, convo_b])
    assert results[0].learned[0].status == "new_candidate"
    assert results[0].learned[0].active is False
    assert results[1].learned[0].status == "activated"
    assert results[1].learned[0].active is True


def test_conversation_evidence_has_conversation_extraction_provenance(session):
    convo = "Meet Aaditya tomorrow."
    with patch.object(entity_extraction, "extract_entities",_mock_extract([("Aaditya", "person")])):
        memory_service.learn_from_conversations(session, [convo])
    mem_id = memory_service.list_memories(session)[0].id
    evidence = memory_service.get_evidence_for(session, mem_id)
    assert len(evidence) == 1
    assert evidence[0].source_type == "conversation_extraction"
    assert evidence[0].source_asr is None
    assert evidence[0].source_corrected == convo


def test_conversation_learned_entity_is_actually_retrievable(session):
    """The test that would catch a normalize_span() mistake: a learned
    conversation-derived memory must actually apply when running a
    transcript, not just exist inertly in the Memory table."""
    from backend.decision import decide
    from backend.formatter import format as format_text
    from backend.retrieval import retrieve
    from backend.tokenizer import tokenize

    convo_a = "Meet Aaditya tomorrow."
    convo_b = "Aaditya confirmed the meeting."
    with patch.object(entity_extraction, "extract_entities",_mock_extract([("Aaditya", "person")])):
        memory_service.learn_from_conversations(session, [convo_a, convo_b])

    formatted = format_text("can you call aditya now")
    tokens = tokenize(formatted)
    candidates = retrieve(session, tokens)
    decisions = decide(tokens, candidates)
    interventions = [d for d in decisions if d.kind == "intervene"]
    assert len(interventions) == 1
    assert interventions[0].canonical_form == "Aaditya"


def test_conversation_empty_text_reports_error_without_aborting_batch(session):
    with patch.object(entity_extraction, "extract_entities",_mock_extract([("Aaditya", "person")])):
        results = memory_service.learn_from_conversations(session, ["Meet Aaditya tomorrow.", "  "])
    assert results[0].error is None and len(results[0].learned) == 1
    assert results[1].error == "conversation text must be non-empty"
