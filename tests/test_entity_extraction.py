from backend import entity_extraction as ee


SOURCE = "Meet Aaditya tomorrow to discuss the Kivi launch in Bengaluru."


def test_valid_accepts_a_real_verbatim_entity():
    item = {"entity_text": "Aaditya", "entity_type": "person"}
    assert ee._valid(item, SOURCE) is True


def test_valid_rejects_hallucinated_span_not_in_source():
    item = {"entity_text": "Rohan", "entity_type": "person"}
    assert ee._valid(item, SOURCE) is False


def test_valid_rejects_disallowed_entity_type():
    item = {"entity_text": "Aaditya", "entity_type": "animal"}
    assert ee._valid(item, SOURCE) is False


def test_valid_rejects_span_longer_than_max_span_tokens(monkeypatch):
    from backend import config
    monkeypatch.setattr(config, "MAX_SPAN_TOKENS", 2)
    item = {"entity_text": "Meet Aaditya tomorrow", "entity_type": "person"}
    assert ee._valid(item, SOURCE) is False


def test_valid_rejects_empty_text():
    assert ee._valid({"entity_text": "  ", "entity_type": "person"}, SOURCE) is False


def test_extract_entities_filters_and_dedupes(monkeypatch):
    monkeypatch.setattr(
        ee, "chat_json",
        lambda *a, **k: [
            {"entity_text": "Aaditya", "entity_type": "person"},
            {"entity_text": "Aaditya", "entity_type": "person"},  # duplicate
            {"entity_text": "Kivi", "entity_type": "product"},
            {"entity_text": "Rohan", "entity_type": "person"},  # not in source - rejected
            {"entity_text": "Bengaluru", "entity_type": "place"},
        ],
    )
    entities = ee.extract_entities(SOURCE)
    texts = sorted(e.entity_text for e in entities)
    assert texts == ["Aaditya", "Bengaluru", "Kivi"]


def test_extract_entities_handles_non_list_response(monkeypatch):
    monkeypatch.setattr(ee, "chat_json", lambda *a, **k: {"not": "a list"})
    assert ee.extract_entities(SOURCE) == []
