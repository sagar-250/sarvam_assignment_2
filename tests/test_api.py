import os

os.environ.setdefault("KIVI_DB_PATH", ":memory:")

import pytest
from fastapi.testclient import TestClient

from backend.db import get_engine
from backend.models import Base


@pytest.fixture()
def client(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_test.db")
    monkeypatch.setenv("KIVI_DB_PATH", db_path)

    import backend.db as db_module

    engine = get_engine(db_path)
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import sessionmaker

    db_module.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    from backend.app import app

    with TestClient(app) as c:
        yield c


def test_observe_run_reset_flow(client):
    r = client.post(
        "/api/observe",
        json={
            "asr": "ask aditya to review the sarvam kiwi service",
            "corrected": "Ask Aaditya to review the Sarvam Kivi service.",
        },
    )
    assert r.status_code == 201
    # "aditya" -> "Aaditya" and "kiwi" -> "Kivi" are spelling corrections;
    # "sarvam" -> "Sarvam" is a mid-sentence casing-only correction, which is
    # also learned (see README "Sentence-initial re-casing never gets
    # learned, but mid-sentence re-casing does").
    assert len(r.json()["learned"]) == 3

    client.post(
        "/api/observe",
        json={
            "asr": "ask aditya to review the sarvam kiwi service",
            "corrected": "Ask Aaditya to review the Sarvam Kivi service.",
        },
    )

    r = client.get("/api/memories")
    assert r.status_code == 200
    assert len(r.json()) == 3

    r = client.post("/api/run", json={"asr": "ask aditya to review the sarvam kiwi service"})
    assert r.status_code == 200
    body = r.json()
    assert body["memory_aware"] == "Ask Aaditya to review the Sarvam Kivi service."
    assert len(body["interventions"]) == 3

    r = client.post("/api/reset")
    assert r.status_code == 200
    assert r.json()["memories_deleted"] == 3

    r = client.get("/api/memories")
    assert r.json() == []


def test_observe_rejects_empty_body(client):
    r = client.post("/api/observe", json={"asr": "", "corrected": "x"})
    assert r.status_code == 400


def test_delete_memory_404(client):
    r = client.delete("/api/memories/999")
    assert r.status_code == 404


def test_bulk_observe_learns_each_pair_and_activates_on_second_confirmation(client):
    r = client.post(
        "/api/observe/bulk",
        json={
            "observations": [
                {"asr": "call rohan now", "corrected": "Call Rohan now"},
                {"asr": "call rohan now", "corrected": "Call Rohan now"},
            ]
        },
    )
    assert r.status_code == 201
    results = r.json()["results"]
    assert len(results) == 2
    assert results[0]["error"] is None
    assert results[0]["learned"][0]["status"] == "new_candidate"
    assert results[0]["learned"][0]["active"] is False
    assert results[1]["learned"][0]["status"] == "activated"
    assert results[1]["learned"][0]["active"] is True

    r = client.get("/api/memories?active_only=true")
    assert len(r.json()) == 1
    assert r.json()[0]["canonical_form"] == "Rohan"


def test_bulk_observe_reports_per_pair_error_without_aborting_batch(client):
    r = client.post(
        "/api/observe/bulk",
        json={
            "observations": [
                {"asr": "call rohan now", "corrected": "Call Rohan now"},
                {"asr": "", "corrected": ""},
                {"asr": "call priya now", "corrected": "Call Priya now"},
            ]
        },
    )
    assert r.status_code == 201
    results = r.json()["results"]
    assert len(results) == 3
    assert results[0]["error"] is None and len(results[0]["learned"]) == 1
    assert results[1]["error"] == "'asr' and 'corrected' must be non-empty"
    assert results[2]["error"] is None and len(results[2]["learned"]) == 1


def test_bulk_observe_rejects_empty_observations(client):
    r = client.post("/api/observe/bulk", json={"observations": []})
    assert r.status_code == 400


def test_learn_from_conversations_rejects_empty_list(client):
    r = client.post("/api/learn-from-conversations", json={"conversations": []})
    assert r.status_code == 400


def test_learn_from_conversations_degrades_to_ner_only_when_credentials_missing(client):
    """Missing LLM credentials must NOT be an error - NER's free first pass
    still runs, so the request succeeds with whatever NER alone found."""
    from unittest.mock import patch

    from backend import entity_extraction, ner_extraction
    from backend.llm_client import LLMCredentialsMissingError

    with patch.object(ner_extraction, "extract_entities_ner", return_value=[
        entity_extraction.ExtractedEntity(entity_text="Aaditya", entity_type="person"),
    ]), patch.object(entity_extraction, "extract_entities", side_effect=LLMCredentialsMissingError("MISTRAL_KEY not found")):
        r = client.post(
            "/api/learn-from-conversations",
            json={"conversations": ["Meet Aaditya tomorrow to discuss the Kivi launch."]},
        )
    assert r.status_code == 200
    learned = r.json()["results"][0]["learned"]
    assert len(learned) == 1
    assert learned[0]["observed_form"] == "aaditya"
    assert learned[0]["sources"] == ["ner"]

    # everything else keeps working right after
    r = client.get("/api/memories")
    assert r.status_code == 200
    r = client.post("/api/run", json={"asr": "hello world"})
    assert r.status_code == 200


def test_learn_from_conversations_reports_error_when_nothing_available(client):
    """If NEITHER the NER model nor LLM credentials are available, the
    conversation gets a clear, actionable error - not a silent empty result."""
    from unittest.mock import patch

    from backend import ner_extraction
    from backend.llm_client import LLMCredentialsMissingError

    with patch.object(ner_extraction, "extract_entities_ner", return_value=[]), \
         patch.object(ner_extraction, "ner_model_available", return_value=False), \
         patch("backend.entity_extraction.extract_entities", side_effect=LLMCredentialsMissingError("no key")):
        r = client.post(
            "/api/learn-from-conversations",
            json={"conversations": ["Meet Aaditya tomorrow."]},
        )
    assert r.status_code == 200
    result = r.json()["results"][0]
    assert result["learned"] == []
    assert result["error"] is not None
    assert "spacy" in result["error"].lower()


def test_learn_from_conversations_merges_ner_and_llm_with_llm_type_winning(client):
    from unittest.mock import patch

    from backend import entity_extraction, ner_extraction

    def fake_llm(text):
        found = [entity_extraction.ExtractedEntity(entity_text="Aaditya", entity_type="person")]
        if "Kivi" in text:
            found.append(entity_extraction.ExtractedEntity(entity_text="Kivi", entity_type="product"))
        return found

    with patch.object(ner_extraction, "extract_entities_ner", return_value=[
        entity_extraction.ExtractedEntity(entity_text="Aaditya", entity_type="other"),  # NER's guess
    ]), patch.object(entity_extraction, "extract_entities", side_effect=fake_llm):
        r = client.post(
            "/api/learn-from-conversations",
            json={"conversations": ["Meet Aaditya tomorrow.", "Aaditya confirmed the Kivi meeting."]},
        )
    assert r.status_code == 200
    results = r.json()["results"]
    first = {l["observed_form"]: l for l in results[0]["learned"]}
    assert first["aaditya"]["entity_type"] == "person"  # LLM's type won on overlap
    assert sorted(first["aaditya"]["sources"]) == ["llm", "ner"]
    assert first["aaditya"]["status"] == "new_candidate"

    second = {l["observed_form"]: l for l in results[1]["learned"]}
    assert second["aaditya"]["status"] == "activated"
    assert second["kivi"]["sources"] == ["llm"]
    assert second["kivi"]["status"] == "new_candidate"

    r = client.get("/api/memories?active_only=true")
    memories = r.json()
    assert len(memories) == 1
    assert memories[0]["canonical_form"] == "Aaditya"
