"""Tests for the word tools. They use the real dictionaries (local files), so nothing is faked."""

import pytest
from fastapi.testclient import TestClient

from app import words
from app.main import app, get_claims
from app.words import lexicon, rhymes

client = TestClient(app)


@pytest.fixture(autouse=True)
def signed_in():
    app.dependency_overrides[get_claims] = lambda: {"sub": "user-1"}
    yield
    app.dependency_overrides.clear()


def names(items):
    return [item["word"] if isinstance(item, dict) else item.word for item in items]


def test_exact_rhymes_share_the_ending_sound():
    known, exact, _ = rhymes.find_rhymes("stone")

    assert known is True
    assert {"alone", "bone", "phone"} <= set(names(exact))
    assert "stone" not in names(exact)


def test_homophones_are_not_rhymes():
    _, exact, near = rhymes.find_rhymes("night")

    assert "knight" not in names(exact) + names(near)


def test_near_rhymes_swap_a_similar_consonant():
    _, exact, near = rhymes.find_rhymes("stone")

    assert "home" in names(near)
    assert "home" not in names(exact)
    assert set(names(exact)).isdisjoint(names(near))


def test_unknown_word_has_no_rhymes():
    assert rhymes.find_rhymes("zzzqx") == (False, [], [])


def test_syllables():
    assert rhymes.syllables_of("stone") == [1]
    assert rhymes.syllables_of("telephone") == [3]


def test_common_words_come_first():
    _, exact, _ = rhymes.find_rhymes("stone")

    assert names(exact).index("alone") < names(exact).index("acetone")


def test_synonyms_and_antonyms():
    synonyms, antonyms = lexicon.related_words("dark")

    assert any("darkness" in group["words"] for group in synonyms)
    assert any("light" in group["words"] for group in antonyms)


def test_endings_are_stripped_to_find_a_word():
    assert lexicon.known_form("stones") == "stone"
    assert lexicon.known_form("hummed") == "hum"
    assert lexicon.known_form("whispers") == "whisper"
    assert lexicon.known_form("zzzqx") is None


def test_clean_word():
    assert words.clean_word("  Don’t ") == "don't"

    with pytest.raises(words.NotAWordError):
        words.clean_word("two words")


def test_route_returns_everything_for_a_word():
    response = client.get("/words/Stone")

    assert response.status_code == 200
    body = response.json()
    assert body["word"] == "stone"
    assert body["rhymes_known"] is True
    assert body["syllables"] == [1]
    assert "alone" in names(body["rhymes"])
    assert "home" in names(body["near_rhymes"])


def test_route_rejects_more_than_one_word():
    assert client.get("/words/two%20words").status_code == 422
    assert client.get("/words/" + "a" * 41).status_code == 422


def test_route_needs_sign_in():
    app.dependency_overrides.clear()

    assert client.get("/words/stone").status_code == 401
