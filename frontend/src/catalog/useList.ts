import { useEffect, useState } from 'react'
import type { ListQuery, Page, Scope, SortOrder } from '../api'
import { describeError } from '../errors'
import { toggleItem } from '../lists'

export const FIRST_PAGE: ListQuery = { q: '', tags: [], year: null, sort: 'newest', page: 1 }

// How long to wait after typing before searching.
const TYPING_DELAY_MS = 300

type ListOptions = {
  /** What the list shows to begin with. */
  first?: ListQuery
  /** Change this to load again (for example when other data this list depends on changed). */
  refreshKey?: number
}

/**
 * One page of a list and the filters that shape it: words, tags, year, order and page number
 * (and, for the mixed list, which kinds). Changing a filter goes back to page 1. An answer that
 * arrives after a newer request was made is dropped.
 */
export function useList<Item>(list: (query: ListQuery) => Promise<Page<Item>>, options: ListOptions = {}) {
  const first = options.first ?? FIRST_PAGE
  const [query, setQuery] = useState<ListQuery>(first)
  const [searchText, setSearchText] = useState('')
  const [page, setPage] = useState<Page<Item> | null>(null)
  const [loadError, setLoadError] = useState('')
  // Goes up after every change to the data, so the page (and the tag list) load again.
  const [version, setVersion] = useState(0)
  const refreshKey = options.refreshKey ?? 0

  // Typing in the search box: wait for a pause, then search from the first page.
  useEffect(() => {
    const timer = setTimeout(() => {
      const words = searchText.trim()

      setQuery((current) => (current.q === words ? current : { ...current, q: words, page: 1 }))
    }, TYPING_DELAY_MS)

    return () => clearTimeout(timer)
  }, [searchText])

  useEffect(() => {
    let active = true

    list(query)
      .then((loaded) => {
        if (active) {
          setPage(loaded)
          setLoadError('')
        }
      })
      .catch((err) => {
        if (active) {
          setLoadError(describeError(err))
        }
      })

    return () => {
      active = false
    }
  }, [list, query, version, refreshKey])

  const hasFilters = Boolean(query.q) || query.tags.length > 0 || Boolean(query.year)

  function toggleTag(tag: string) {
    setQuery((current) => ({ ...current, tags: toggleItem(current.tags, tag), page: 1 }))
  }

  function setYear(year: number | null) {
    setQuery((current) => ({ ...current, year, page: 1 }))
  }

  function setSort(sort: SortOrder) {
    setQuery((current) => ({ ...current, sort, page: 1 }))
  }

  function setScope(scope: Scope) {
    setQuery((current) => ({ ...current, scope, page: 1 }))
  }

  function goToPage(number: number) {
    setQuery((current) => ({ ...current, page: number }))
  }

  function clearFilters() {
    setSearchText('')
    setQuery((current) => ({ ...first, sort: current.sort, scope: current.scope }))
  }

  /** Load the list again, after the data changed. */
  function reload() {
    setVersion((current) => current + 1)
  }

  /** Show the first page, newest first (where a new item appears). */
  function showNewest() {
    setQuery((current) => ({ ...current, sort: 'newest', page: 1 }))
  }

  return {
    page,
    query,
    hasFilters,
    version,
    loadError,
    searchText,
    setSearchText,
    toggleTag,
    setYear,
    setSort,
    setScope,
    goToPage,
    clearFilters,
    reload,
    showNewest,
  }
}
