from backend.tokenizer import tokenize, span_norm


def test_basic_tokenize():
    tokens = tokenize("Ask Aditya to review.")
    assert [t.text for t in tokens] == ["Ask", "Aditya", "to", "review"]
    assert [t.norm for t in tokens] == ["ask", "aditya", "to", "review"]


def test_possessive_detection():
    tokens = tokenize("aditya's presentation")
    assert tokens[0].base == "aditya"
    assert tokens[0].is_possessive is True
    assert tokens[0].possessive_suffix == "'s"


def test_offsets_allow_reconstruction():
    text = "Hello, aditya!  Are you free?"
    tokens = tokenize(text)
    for t in tokens:
        assert text[t.start : t.end] == t.text


def test_span_norm_multiword():
    tokens = tokenize("New York City")
    assert span_norm(tokens[:2]) == "new york"
