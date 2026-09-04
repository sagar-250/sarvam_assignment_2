from backend import ner_extraction


def test_ner_model_is_available_in_this_environment():
    # This test environment has en_core_web_sm installed (see RUN.md); if this
    # ever fails, run: python -m spacy download en_core_web_sm
    assert ner_extraction.ner_model_available() is True


def test_finds_places_and_orgs_reliably():
    entities = ner_extraction.extract_entities_ner(
        "Meet me tomorrow to discuss the launch in Mumbai with Google."
    )
    texts = {e.entity_text: e.entity_type for e in entities}
    assert texts.get("Mumbai") == "place"
    assert texts.get("Google") == "product"


def test_finds_a_name_with_strong_verb_context():
    entities = ner_extraction.extract_entities_ner("Sarah called. Sarah left a message.")
    texts = {e.entity_text: e.entity_type for e in entities}
    assert texts.get("Sarah") == "person"


def test_deduplicates_repeated_mentions():
    entities = ner_extraction.extract_entities_ner(
        "Sarah called. Sarah left a message. Sarah will call back."
    )
    assert [e.entity_text for e in entities].count("Sarah") == 1


def test_verified_recall_gap_on_south_asian_names_without_verb_context():
    """Documents a real, verified gap (not assumed): en_core_web_sm misses
    'Rahul' as PERSON entirely here, in a sentence structure where it also
    misses the equally name-shaped 'John' - but reliably catches 'Sarah'
    when there's a supporting verb context ('called', 'left a message').
    This is the concrete evidence behind backend/ner_extraction.py's
    docstring and README's design rationale for keeping the LLM pass as a
    refinement, not treating NER alone as sufficient."""
    entities = ner_extraction.extract_entities_ner(
        "Meet Rahul tomorrow to discuss the launch in Mumbai with Google."
    )
    texts = {e.entity_text for e in entities}
    assert "Rahul" not in texts
    assert {"Mumbai", "Google"} <= texts


def test_drops_entity_types_outside_the_supported_vocabulary():
    # "tomorrow" (DATE) and "five" (CARDINAL) should never become candidate
    # memories - only PERSON/ORG/PRODUCT/GPE/LOC/FAC map to a supported type.
    entities = ner_extraction.extract_entities_ner("Call me tomorrow, I'll bring five reports.")
    assert all(e.entity_type in {"person", "product", "place"} for e in entities)


def test_returns_empty_list_when_model_unavailable(monkeypatch):
    monkeypatch.setattr(ner_extraction, "_load_model", lambda: None)
    assert ner_extraction.extract_entities_ner("Meet Rahul tomorrow.") == []
    assert ner_extraction.ner_model_available() is False
