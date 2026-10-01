import pytest
from pydantic import ValidationError

from app.models import (
    MAX_FRAGMENT_TEXT,
    MAX_SONG_BODY,
    MAX_TAG_LENGTH,
    MAX_TAGS,
    MAX_TITLE,
    FragmentIn,
    SongIn,
)


def test_song_requires_a_title():
    with pytest.raises(ValidationError):
        SongIn(title="   ")


def test_song_trims_title_and_body_defaults_to_empty():
    song = SongIn(title="  Blue Door  ")
    assert song.title == "Blue Door"
    assert song.body == ""


def test_song_title_and_body_have_length_limits():
    SongIn(title="a" * MAX_TITLE, body="b" * MAX_SONG_BODY)
    with pytest.raises(ValidationError):
        SongIn(title="a" * (MAX_TITLE + 1))
    with pytest.raises(ValidationError):
        SongIn(title="ok", body="b" * (MAX_SONG_BODY + 1))


def test_fragment_requires_text():
    with pytest.raises(ValidationError):
        FragmentIn(text="  ")


def test_fragment_text_has_a_length_limit():
    FragmentIn(text="a" * MAX_FRAGMENT_TEXT)
    with pytest.raises(ValidationError):
        FragmentIn(text="a" * (MAX_FRAGMENT_TEXT + 1))


def test_fragment_tags_default_to_empty():
    assert FragmentIn(text="a line").tags == []


def test_tags_are_trimmed_lowercased_and_deduplicated():
    fragment = FragmentIn(text="a line", tags=["Love", "love ", " RAIN", "", "rain"])
    assert fragment.tags == ["love", "rain"]


def test_too_many_tags_are_rejected():
    FragmentIn(text="a line", tags=[f"t{i}" for i in range(MAX_TAGS)])
    with pytest.raises(ValidationError):
        FragmentIn(text="a line", tags=[f"t{i}" for i in range(MAX_TAGS + 1)])


def test_a_tag_that_is_too_long_is_rejected():
    FragmentIn(text="a line", tags=["a" * MAX_TAG_LENGTH])
    with pytest.raises(ValidationError):
        FragmentIn(text="a line", tags=["a" * (MAX_TAG_LENGTH + 1)])
