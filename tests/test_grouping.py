from backend import config, grouping
from backend.diff import ObservationPair


def _pairs():
    return [
        ObservationPair(observed_form="new", canonical_form="New", token_count=1, entity_type="other"),
        ObservationPair(observed_form="yolk sity", canonical_form="York City", token_count=2, entity_type="other"),
    ]


def test_disabled_by_default_is_a_pure_noop(monkeypatch):
    called = False

    def _fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("chat_json should never be called when grouping is disabled")

    monkeypatch.setattr(grouping, "chat_json", _fail_if_called)
    assert config.KIVI_LLM_GROUPING_ENABLED is False

    pairs, attempted = grouping.maybe_group_adjacent_pairs(_pairs(), "Flying to New York City")
    assert pairs == _pairs()
    assert attempted is False
    assert called is False


def test_enabled_merges_when_llm_says_one_entity(monkeypatch):
    monkeypatch.setattr(config, "KIVI_LLM_GROUPING_ENABLED", True)
    monkeypatch.setattr(
        grouping, "chat_json",
        lambda *a, **k: {"merge": True, "entity_type": "place"},
    )

    pairs, attempted = grouping.maybe_group_adjacent_pairs(_pairs(), "Flying to New York City")
    assert attempted is True
    assert len(pairs) == 1
    assert pairs[0].observed_form == "new yolk sity"
    assert pairs[0].canonical_form == "New York City"
    assert pairs[0].token_count == 3
    assert pairs[0].entity_type == "place"


def test_enabled_keeps_separate_when_llm_says_two_entities(monkeypatch):
    monkeypatch.setattr(config, "KIVI_LLM_GROUPING_ENABLED", True)
    monkeypatch.setattr(grouping, "chat_json", lambda *a, **k: {"merge": False, "entity_type": "other"})

    sarvam_kiwi = [
        ObservationPair(observed_form="sarvam", canonical_form="Sarvam", token_count=1, entity_type="product"),
        ObservationPair(observed_form="kiwi", canonical_form="Kivi", token_count=1, entity_type="product"),
    ]
    pairs, attempted = grouping.maybe_group_adjacent_pairs(
        sarvam_kiwi, "Ask Aaditya to review the Sarvam Kivi service."
    )
    assert attempted is True
    assert len(pairs) == 2
    assert [p.canonical_form for p in pairs] == ["Sarvam", "Kivi"]


def test_missing_credentials_falls_back_to_unchanged_pairs(monkeypatch):
    monkeypatch.setattr(config, "KIVI_LLM_GROUPING_ENABLED", True)

    def _raise_missing(*a, **k):
        raise grouping.LLMCredentialsMissingError("no key configured")

    monkeypatch.setattr(grouping, "chat_json", _raise_missing)

    pairs, attempted = grouping.maybe_group_adjacent_pairs(_pairs(), "Flying to New York City")
    assert pairs == _pairs()
    assert attempted is False


def test_malformed_llm_response_falls_back_without_crashing(monkeypatch):
    monkeypatch.setattr(config, "KIVI_LLM_GROUPING_ENABLED", True)
    monkeypatch.setattr(grouping, "chat_json", lambda *a, **k: "not a dict")

    pairs, attempted = grouping.maybe_group_adjacent_pairs(_pairs(), "Flying to New York City")
    assert attempted is True
    assert len(pairs) == 2  # merge defaulted to False, nothing merged


def test_non_adjacent_pairs_are_never_offered_to_the_llm(monkeypatch):
    monkeypatch.setattr(config, "KIVI_LLM_GROUPING_ENABLED", True)
    called = False

    def _fail_if_called(*a, **k):
        nonlocal called
        called = True
        return {"merge": True, "entity_type": "other"}

    monkeypatch.setattr(grouping, "chat_json", _fail_if_called)

    sarvam_kiwi = [
        ObservationPair(observed_form="sarvam", canonical_form="Sarvam", token_count=1, entity_type="product"),
        ObservationPair(observed_form="kiwi", canonical_form="Kivi", token_count=1, entity_type="product"),
    ]
    # "Sarvam" and "Kivi" are NOT written adjacently in this corrected text
    # ("the" sits between them) - grouping must not even ask the LLM.
    pairs, attempted = grouping.maybe_group_adjacent_pairs(
        sarvam_kiwi, "Ask Aaditya to review the Sarvam the Kivi service."
    )
    assert attempted is False
    assert called is False
    assert len(pairs) == 2
