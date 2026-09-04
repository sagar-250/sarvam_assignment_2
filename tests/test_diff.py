from backend.diff import extract_observations


def test_brief_example_produces_exactly_two_pairs():
    asr = "ask aditya to review the sarvam kiwi service"
    corrected = "Ask Aaditya to review the Sarvam Kivi service."
    pairs, formatted = extract_observations(asr, corrected)

    assert formatted == "Ask aditya to review the sarvam kiwi service."

    by_observed = {p.observed_form: p for p in pairs}
    assert set(by_observed) == {"aditya", "kiwi", "sarvam"}
    assert by_observed["aditya"].canonical_form == "Aaditya"
    assert by_observed["kiwi"].canonical_form == "Kivi"


def test_mid_sentence_pure_casing_is_learned():
    pairs, _ = extract_observations("call sohail now", "Call Sohail now")
    assert len(pairs) == 1
    assert pairs[0].observed_form == "sohail"
    assert pairs[0].canonical_form == "Sohail"


def test_sentence_initial_pure_casing_is_not_learned():
    pairs, _ = extract_observations("sohail is here", "Sohail is here")
    assert pairs == []


def test_recasing_adjacent_to_replace_learns_both_as_separate_pairs():
    pairs, _ = extract_observations("flying to new yolk sity", "Flying to New York City")
    by_observed = {p.observed_form: p for p in pairs}
    assert by_observed["new"].canonical_form == "New"
    assert by_observed["yolk sity"].canonical_form == "York City"


def test_insert_after_equal_is_merged_into_a_pair():
    pairs, _ = extract_observations(
        "apple released a new update", "Apple Inc. released a new update"
    )
    assert len(pairs) == 1
    assert pairs[0].observed_form == "apple"
    assert pairs[0].canonical_form == "Apple Inc"


def test_already_correct_input_produces_no_pairs():
    pairs, _ = extract_observations("Aaditya is here", "Aaditya is here")
    assert pairs == []


def test_entity_type_is_localized_not_whole_sentence():
    pairs, _ = extract_observations(
        "ask aditya to review the sarvam kiwi service",
        "Ask Aaditya to review the Sarvam Kivi service.",
    )
    by_observed = {p.observed_form: p for p in pairs}
    assert by_observed["aditya"].entity_type == "person"
    assert by_observed["kiwi"].entity_type == "product"
