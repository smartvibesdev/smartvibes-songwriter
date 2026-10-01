"""Request and response shapes for songs and fragments (plan section 5)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints, field_validator

MAX_TITLE = 200
MAX_SONG_BODY = 20_000
MAX_FRAGMENT_TEXT = 2_000
MAX_TAGS = 10
MAX_TAG_LENGTH = 30


class SongIn(BaseModel):
    """What a client sends to create or replace a song."""

    title: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TITLE),
    ]
    body: Annotated[str, StringConstraints(max_length=MAX_SONG_BODY)] = ""


class Song(SongIn):
    """A stored song, as returned by the API."""

    id: str
    created_at: datetime
    updated_at: datetime


class FragmentIn(BaseModel):
    """What a client sends to create or replace a fragment."""

    text: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=MAX_FRAGMENT_TEXT
        ),
    ]
    tags: list[str] = []

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, tags: list[str]) -> list[str]:
        """Trim, lowercase, drop blanks and duplicates (keeping first-seen order)."""
        cleaned: list[str] = []
        for tag in tags:
            tag = tag.strip().lower()
            if not tag:
                continue
            if len(tag) > MAX_TAG_LENGTH:
                raise ValueError(f"tag longer than {MAX_TAG_LENGTH} characters")
            if tag not in cleaned:
                cleaned.append(tag)
        if len(cleaned) > MAX_TAGS:
            raise ValueError(f"more than {MAX_TAGS} tags")
        return cleaned


class Fragment(FragmentIn):
    """A stored fragment, as returned by the API."""

    id: str
    created_at: datetime
    updated_at: datetime


class SearchResults(BaseModel):
    """Keyword-search matches, grouped by kind. Each list is newest first."""

    songs: list[Song]
    fragments: list[Fragment]
