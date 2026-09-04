from backend import memory_service
from backend.decision import decide
from backend.retrieval import retrieve
from backend.tokenizer import tokenize


def _activate(session, asr, corrected, times=2):
    for _ in range(times):
        memory_service.learn(session, asr, corrected)


def _run(session, text):
    tokens = tokenize(text)
    cands = retrieve(session, tokens)
    return tokens, decide(tokens, cands)


def test_active_memory_intervenes(session):
    _activate(session, "call aditya now", "Call Aaditya now")
    _, decisions = _run(session, "Email aditya please.")
    assert len(decisions) == 1
    assert decisions[0].kind == "intervene"
    assert decisions[0].canonical_form == "Aaditya"
    assert decisions[0].reason == "active_memory_high_confidence"


def test_below_confidence_threshold_no_intervene(session):
    _activate(session, "call aditya now", "Call Aaditya now", times=1)
    _, decisions = _run(session, "Email aditya please.")
    assert len(decisions) == 1
    assert decisions[0].kind == "no_intervene"
    assert decisions[0].reason == "below_confidence_threshold"


def test_already_correct_no_intervene(session):
    _activate(session, "call aditya now", "Call Aaditya now")
    _, decisions = _run(session, "Email Aaditya please.")
    assert len(decisions) == 1
    assert decisions[0].kind == "no_intervene"
    assert decisions[0].reason == "already_correct"


def test_ambiguous_common_word_blocked_without_context(session):
    _activate(session, "apple released a new update", "Apple Inc. released a new update")
    _, decisions = _run(session, "I ate an apple today.")
    assert len(decisions) == 1
    assert decisions[0].kind == "no_intervene"
    assert decisions[0].reason == "ambiguous_common_word_no_supporting_context"


def test_ambiguous_common_word_allowed_with_context(session):
    _activate(session, "apple released a new update", "Apple Inc. released a new update")
    _, decisions = _run(session, "Apple announced a new release today.")
    assert len(decisions) == 1
    assert decisions[0].kind == "intervene"
    assert decisions[0].canonical_form == "Apple Inc"


def test_possessive_preserved_in_decision(session):
    _activate(session, "call aditya now", "Call Aaditya now")
    _, decisions = _run(session, "This is aditya's presentation.")
    assert decisions[0].kind == "intervene"
    assert decisions[0].canonical_form == "Aaditya"
