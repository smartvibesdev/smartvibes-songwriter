"""Request and response shapes for songs and fragments (plan section 5)."""

from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.ai.prompts import DIAL_MAX, DIAL_MIN, MAX_SEED_LENGTH

MAX_TITLE = 200
MAX_SONG_BODY = 20_000
MAX_FRAGMENT_TEXT = 2_000
MAX_TAGS = 10
MAX_TAG_LENGTH = 30

# Which kinds of item a search or tag list covers.
Scope = Literal["both", "songs", "fragments"]

# How a list is ordered: by when the item was created.
Sort = Literal["newest", "oldest"]

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def clean_tags(tags: list[str]) -> list[str]:
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


# Songs and fragments share the same tag rules.
TagList = Annotated[list[str], AfterValidator(clean_tags)]


class SongIn(BaseModel):
    """What a client sends to create or replace a song."""

    title: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TITLE),
    ]
    body: Annotated[str, StringConstraints(max_length=MAX_SONG_BODY)] = ""
    tags: TagList = []


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
    tags: TagList = []


class Fragment(FragmentIn):
    """A stored fragment, as returned by the API."""

    id: str
    created_at: datetime
    updated_at: datetime


class SearchResults(BaseModel):
    """Search matches, grouped by kind: the first few of each, newest first.

    `song_total` and `fragment_total` count every match, so the screen can say
    "showing 20 of 1,753".
    """

    songs: list[Song]
    fragments: list[Fragment]
    song_total: int = 0
    fragment_total: int = 0


class TagCount(BaseModel):
    """A tag and how many items carry it."""

    tag: str
    count: int


class YearCount(BaseModel):
    """A year and how many matching items were created in it."""

    year: int
    count: int


ItemT = TypeVar("ItemT")


class Page(BaseModel, Generic[ItemT]):
    """One page of a filtered, sorted list of songs or fragments."""

    items: list[ItemT]
    # How many items match the current filters, across all pages.
    total: int
    # How many items of this kind exist, before any filter.
    all_count: int
    page: int
    page_size: int
    pages: int
    # Years that have matches (ignoring the year filter), newest first.
    years: list[YearCount]


class ListParams(BaseModel):
    """Query parameters for a song or fragment list."""

    model_config = ConfigDict(extra="forbid")

    q: str = Field("", max_length=100)
    tag: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    year: int | None = Field(None, ge=1900, le=2200)
    sort: Sort = "newest"
    page: int = Field(1, ge=1)
    page_size: int = Field(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)


class SongEntry(Song):
    """A song in a mixed list of songs and fragments."""

    kind: Literal["song"] = "song"


class FragmentEntry(Fragment):
    """A fragment in a mixed list of songs and fragments."""

    kind: Literal["fragment"] = "fragment"


# One row of the Home list: either a song or a fragment, told apart by `kind`.
NotebookEntry = Annotated[SongEntry | FragmentEntry, Field(discriminator="kind")]


class NotebookParams(ListParams):
    """Query parameters for the mixed list on Home: the list parameters plus which kinds."""

    scope: Scope = "both"


class GenerateIn(BaseModel):
    """What a client sends to ask for generated text."""

    kind: Literal["title", "lyrics", "fragment"]
    # Optional starting idea or text. Empty means "invent something".
    seed: Annotated[str, StringConstraints(max_length=MAX_SEED_LENGTH)] = ""
    # The wildness dial: 0 is predictable, 10 is wild.
    dial: int = Field(5, ge=DIAL_MIN, le=DIAL_MAX)


class TokenCount(BaseModel):
    input: int
    output: int


class BudgetOut(BaseModel):
    """The signed-in user's AI token budget for today (UTC), for the token meter."""

    used: int
    limit: int
    remaining: int


class GenerateOut(BaseModel):
    kind: Literal["title", "lyrics", "fragment"]
    text: str
    dial: int
    # The temperature that was sent to Claude (0 to 1).
    temperature: float
    tokens: TokenCount
    budget: BudgetOut
