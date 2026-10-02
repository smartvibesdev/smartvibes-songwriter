# 0013. App-level state for the screens

- Status: Accepted
- Date: 2026-10-02

## Context

Each screen used to keep its own state, and pages were removed from the screen when you
switched tabs, which threw away search text, filters, the page number and the loaded list,
and loaded everything again on the next visit. The owner wanted to keep their place, and
later wants more screens (a song editor, ideas) that share the same data.

Songs and Fragments briefly had their own pages. Home (search and filter over both kinds)
made them duplicates, so on 2026-10-02 they were removed and Home became the one list.
Adding a song or fragment moved to a "+ New" menu on Home.

## Options considered

- **Keep every page mounted and hide the inactive ones.** Very little code and keeps even
  the scroll position, but there is nowhere to load data from before a page is shown.
- **A state library** (Redux, Zustand, TanStack Query). Powerful, with caching built in,
  but a new dependency and more concepts for what is a small app.
- **A React context that holds the screens' state** (chosen). No new dependency, one place
  to look.

## Decision

- `AppStateProvider` (`src/state/`) wraps the signed-in app. It holds Home's mixed list
  (words, tags, year, sort, which kinds, page number and the loaded page), its tag list, the
  random fragment, and the editing and deleting state for songs and fragments. Screens read
  it through `useAppState()`.
- Adding, editing or deleting a song or fragment reloads Home's list and tags.
- Signing out removes the provider, so nothing carries over to the next person.
- A response that arrives after a newer request was made is ignored, in every loader.

## Consequences

- New screens (the song editor, ideas) can read and change the same data without each one
  loading it again.
- Data does not refresh by itself. If another device changes your notebook, this one shows
  the older list until you search, change a filter or reload. A refresh-when-stale rule can
  be added later.
- A screen that is removed and added again starts at the top of its list.
- Everything in the store stays in memory for the session. At 20 items per page that is small.
- Loading the first page of songs or fragments ahead of time is no longer a separate step:
  Home loads its list as soon as the app opens.
