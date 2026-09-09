"""backend.retrieval routes to a different matching strategy depending on
memory-table size (see config.RETRIEVAL_SMALL_TABLE_THRESHOLD). These tests
force each strategy directly and check they agree on the same input -
that's the actual risk a router introduces: two independent code paths
silently drifting apart."""
from backend import memory_service
from backend.retrieval import Candidate, _retrieve_large, _retrieve_small
from backend.tokenizer import tokenize


def _activate(session, asr, corrected, times=2):
    for _ in range(times):
        memory_service.learn(session, asr, corrected)


def _as_tuples(candidates: list[Candidate]) -> set[tuple]:
    return {
        (c.start_idx, c.end_idx, c.memory.id, c.match_type, c.edit_distance)
        for c in candidates
    }


def test_small_and_large_paths_agree_on_exact_and_fuzzy(session):
    _activate(session, "call aditya now", "Call Aaditya now")
    _activate(session, "flying to new yolk sity", "Flying to New York City")
    tokens = tokenize("Email adithya about new yolk sity please.")

    small = _retrieve_small(session, tokens)
    large = _retrieve_large(session, tokens)

    assert _as_tuples(small) == _as_tuples(large)
    assert len(small) > 0  # sanity: this scenario actually exercises both match types


def test_small_and_large_paths_agree_on_no_match(session):
    _activate(session, "call aditya now", "Call Aaditya now")
    tokens = tokenize("Completely unrelated sentence here.")

    assert _retrieve_small(session, tokens) == []
    assert _retrieve_large(session, tokens) == []


def test_small_and_large_paths_agree_on_inactive_candidates(session):
    _activate(session, "call aditya now", "Call Aaditya now", times=1)
    tokens = tokenize("Email aditya please.")

    small = _retrieve_small(session, tokens)
    large = _retrieve_large(session, tokens)

    assert _as_tuples(small) == _as_tuples(large)
    assert len(small) == 1
    assert small[0].memory.active is False


def test_router_picks_small_path_below_threshold(session, monkeypatch):
    from backend import config, retrieval

    calls = []
    monkeypatch.setattr(retrieval, "_retrieve_small", lambda s, t: calls.append("small") or [])
    monkeypatch.setattr(retrieval, "_retrieve_large", lambda s, t: calls.append("large") or [])
    monkeypatch.setattr(config, "RETRIEVAL_SMALL_TABLE_THRESHOLD", 2000)

    retrieval.retrieve(session, tokenize("hello world"))
    assert calls == ["small"]


def test_router_picks_large_path_above_threshold(session, monkeypatch):
    from backend import config, memory_service, retrieval

    _activate(session, "call aditya now", "Call Aaditya now")

    calls = []
    monkeypatch.setattr(retrieval, "_retrieve_small", lambda s, t: calls.append("small") or [])
    monkeypatch.setattr(retrieval, "_retrieve_large", lambda s, t: calls.append("large") or [])
    monkeypatch.setattr(config, "RETRIEVAL_SMALL_TABLE_THRESHOLD", 0)

    retrieval.retrieve(session, tokenize("hello world"))
    assert calls == ["large"]
