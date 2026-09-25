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


# --- ONNX NER grouping: fake the model so these run without it installed ---

import pytest

from backend import onnx_ner


def _pair(observed, canonical, entity_type="other"):
    return ObservationPair(
        observed_form=observed, canonical_form=canonical,
        token_count=len(observed.split()), entity_type=entity_type,
    )


def _fake_ner(monkeypatch, entities):
    """entities: [(surface_text, entity_type)] - spans are located by find()."""
    monkeypatch.setattr(config, "KIVI_NER_GROUPING_ENABLED", True)
    monkeypatch.setattr(onnx_ner, "onnx_ner_available", lambda: True)

    def _spans(text):
        out = []
        for surface, entity_type in entities:
            start = text.find(surface)
            if start != -1:
                out.append((start, start + len(surface), entity_type))
        return out

    monkeypatch.setattr(onnx_ner, "extract_entity_spans", _spans)


def test_ner_merges_multiword_place_into_one_memory(monkeypatch):
    _fake_ner(monkeypatch, [("Abu Dhabi", "place")])
    pairs, attempted = grouping.maybe_group_adjacent_pairs(
        [_pair("abu", "Abu"), _pair("dabi", "Dhabi")], "The layover is in Abu Dhabi"
    )
    assert attempted is False
    assert [(p.observed_form, p.canonical_form, p.token_count, p.entity_type) for p in pairs] == [
        ("abu dabi", "Abu Dhabi", 2, "place")
    ]


def test_ner_merges_three_word_run_so_common_words_are_not_learned_alone(monkeypatch):
    _fake_ner(monkeypatch, [("Salt Lake City", "place")])
    pairs, _ = grouping.maybe_group_adjacent_pairs(
        [_pair("salt", "Salt"), _pair("lake", "Lake"), _pair("city", "City")],
        "The ski trip is to Salt Lake City",
    )
    assert [p.canonical_form for p in pairs] == ["Salt Lake City"]
    assert pairs[0].token_count == 3


def test_ner_merges_person_full_name(monkeypatch):
    _fake_ner(monkeypatch, [("Vikram Chowdhury", "person")])
    pairs, _ = grouping.maybe_group_adjacent_pairs(
        [_pair("vikram", "Vikram"), _pair("chaudhary", "Chowdhury")],
        "Schedule a call with Vikram Chowdhury",
    )
    assert [(p.observed_form, p.entity_type) for p in pairs] == [("vikram chaudhary", "person")]


def test_ner_only_merges_the_covered_pairs(monkeypatch):
    _fake_ner(monkeypatch, [("Anjali", "person"), ("Abu Dhabi", "place")])
    pairs, _ = grouping.maybe_group_adjacent_pairs(
        [_pair("anjalee", "Anjali"), _pair("abu", "Abu"), _pair("dabi", "Dhabi")],
        "Ask Anjali to visit Abu Dhabi",
    )
    assert [p.canonical_form for p in pairs] == ["Anjali", "Abu Dhabi"]


def test_ner_product_span_is_not_merged_and_falls_through_to_llm(monkeypatch):
    # "Sarvam Kivi" as one ORG span must NOT be trusted - two products - but
    # the LLM (when enabled) still gets asked instead of being skipped.
    _fake_ner(monkeypatch, [("Sarvam Kivi", "product")])
    monkeypatch.setattr(config, "KIVI_LLM_GROUPING_ENABLED", True)
    asked = []
    monkeypatch.setattr(
        grouping, "chat_json", lambda *a, **k: asked.append(1) or {"merge": False, "entity_type": "other"}
    )
    pairs, attempted = grouping.maybe_group_adjacent_pairs(
        [_pair("sarvam", "Sarvam", "product"), _pair("kiwi", "Kivi", "product")],
        "Ask Aaditya to review the Sarvam Kivi service.",
    )
    assert [p.canonical_form for p in pairs] == ["Sarvam", "Kivi"]
    assert asked and attempted is True


def test_ner_product_span_stays_separate_without_llm(monkeypatch):
    _fake_ner(monkeypatch, [("Sarvam Kivi", "product")])
    pairs, attempted = grouping.maybe_group_adjacent_pairs(
        [_pair("sarvam", "Sarvam"), _pair("kiwi", "Kivi")], "Review the Sarvam Kivi service."
    )
    assert [p.canonical_form for p in pairs] == ["Sarvam", "Kivi"]
    assert attempted is False


def test_ner_unavailable_is_a_noop(monkeypatch):
    monkeypatch.setattr(config, "KIVI_NER_GROUPING_ENABLED", True)
    monkeypatch.setattr(onnx_ner, "onnx_ner_available", lambda: False)
    original = [_pair("abu", "Abu"), _pair("dabi", "Dhabi")]
    pairs, attempted = grouping.maybe_group_adjacent_pairs(list(original), "The layover is in Abu Dhabi")
    assert pairs == original
    assert attempted is False


def test_ner_merge_respects_max_span_tokens(monkeypatch):
    _fake_ner(monkeypatch, [("Kuala Lumpur Sentral Station", "place")])
    monkeypatch.setattr(config, "MAX_SPAN_TOKENS", 2)
    pairs, _ = grouping.maybe_group_adjacent_pairs(
        [_pair("kuala", "Kuala"), _pair("lumpoor", "Lumpur"), _pair("sentral", "Sentral")],
        "Meet at Kuala Lumpur Sentral Station",
    )
    assert [p.canonical_form for p in pairs] == ["Kuala Lumpur", "Sentral"]


# --- real model, only when an export is installed at KIVI_ONNX_NER_DIR ---

@pytest.mark.skipif(not onnx_ner.onnx_ner_available(), reason="ONNX NER export not installed")
@pytest.mark.parametrize("asr,corrected,expected", [
    ("the layover is in abu dabi", "The layover is in Abu Dhabi", "Abu Dhabi"),
    ("the conference is in san fransisco", "The conference is in San Francisco", "San Francisco"),
    ("schedule a call with vikram chaudhary", "Schedule a call with Vikram Chowdhury", "Vikram Chowdhury"),
    ("the warehouse moved to navi mumbai", "The warehouse moved to Navi Mumbai", "Navi Mumbai"),
])
def test_real_onnx_ner_merges_multiword_names(monkeypatch, asr, corrected, expected):
    from backend.diff import extract_observations

    monkeypatch.setattr(config, "KIVI_NER_GROUPING_ENABLED", True)
    pairs, _ = extract_observations(asr, corrected)
    grouped, _ = grouping.maybe_group_adjacent_pairs(pairs, corrected)
    assert expected in [p.canonical_form for p in grouped]


@pytest.mark.skipif(not onnx_ner.onnx_ner_available(), reason="ONNX NER export not installed")
def test_real_onnx_ner_keeps_sarvam_kivi_separate(monkeypatch):
    from backend.diff import extract_observations

    monkeypatch.setattr(config, "KIVI_NER_GROUPING_ENABLED", True)
    corrected = "Ask Aaditya to review the Sarvam Kivi service"
    pairs, _ = extract_observations("ask aditya to review the sarvam kiwi service", corrected)
    grouped, _ = grouping.maybe_group_adjacent_pairs(pairs, corrected)
    assert "Sarvam Kivi" not in [p.canonical_form for p in grouped]
