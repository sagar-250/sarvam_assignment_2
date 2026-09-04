from backend import memory_service
from backend.retrieval import retrieve
from backend.tokenizer import tokenize


def _activate(session, asr, corrected, times=2):
    for _ in range(times):
        memory_service.learn(session, asr, corrected)


def test_exact_match_found(session):
    _activate(session, "call aditya now", "Call Aaditya now")
    tokens = tokenize("Email aditya please.")
    cands = retrieve(session, tokens)
    assert len(cands) == 1
    assert cands[0].match_type == "exact"
    assert cands[0].memory.canonical_form == "Aaditya"


def test_fuzzy_match_within_budget(session):
    _activate(session, "call aditya now", "Call Aaditya now")
    tokens = tokenize("Email adithya please.")
    cands = retrieve(session, tokens)
    assert len(cands) == 1
    assert cands[0].match_type == "fuzzy"
    assert cands[0].edit_distance == 1


def test_fuzzy_reject_too_far(session):
    _activate(session, "call aditya now", "Call Aaditya now")
    tokens = tokenize("Email rajesh please.")
    cands = retrieve(session, tokens)
    assert cands == []


def test_inactive_candidate_still_surfaced(session):
    _activate(session, "call aditya now", "Call Aaditya now", times=1)
    tokens = tokenize("Email aditya please.")
    cands = retrieve(session, tokens)
    assert len(cands) == 1
    assert cands[0].memory.active is False


def test_multiword_observed_span_matched(session):
    _activate(session, "flying to new yolk sity", "Flying to New York City")
    tokens = tokenize("Visit new yolk sity tomorrow.")
    cands = retrieve(session, tokens)
    by_span = {(c.start_idx, c.end_idx): c for c in cands}
    assert (1, 2) in by_span and by_span[(1, 2)].memory.canonical_form == "New"
    assert (2, 4) in by_span
    assert by_span[(2, 4)].memory.canonical_form == "York City"
    assert by_span[(2, 4)].memory.token_count == 2
