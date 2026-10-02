import { getIdToken } from './auth'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Shapes returned by the backend (see backend/app/models.py). Dates are ISO strings.

export type SongInput = { title: string; body: string; tags: string[] }
export type Song = SongInput & { id: string; created_at: string; updated_at: string }

export type FragmentInput = { text: string; tags: string[] }
export type Fragment = FragmentInput & { id: string; created_at: string; updated_at: string }

export type SearchResults = { songs: Song[]; fragments: Fragment[] }

/** Which kinds of item a search or tag list covers. */
export type Scope = 'both' | 'songs' | 'fragments'

export type TagCount = { tag: string; count: number }

/** Size limits enforced by the backend (keep in sync with backend/app/models.py). */
export const LIMITS = { title: 200, songBody: 20_000, fragmentText: 2_000 }

/** A failed API call. `status` is the HTTP status, or 0 if the server was unreachable. */
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)

    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * One problem in a FastAPI validation error (HTTP 422).
 * `loc` is the path to the bad value, e.g. ['body', 'title']. Its first entry is always 'body' or 'query'.
 */
type ValidationProblem = { loc: (string | number)[]; msg: string }

/** The JSON body of an error response: `detail` is a message, or a list of validation problems. */
type ErrorBody = { detail?: string | ValidationProblem[] }

/** Describes one validation problem, e.g. "title: String should have at least 1 character". */
function describeProblem(problem: ValidationProblem): string {
  const field = problem.loc.slice(1).join('.')

  if (field) {
    return `${field}: ${problem.msg}`
  }

  return problem.msg
}

/** Turns a failed response into one readable message. */
function errorMessage(status: number, body: ErrorBody | null): string {
  const detail = body?.detail

  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map(describeProblem).join('; ')
  }

  return `Request failed (${status})`
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const token = await getIdToken()

  if (token === null) {
    throw new ApiError(401, 'You are signed out. Please sign in again.')
  }

  let response: Response

  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'Could not reach the server.')
  }

  // 204 No Content (a successful delete) has no body to read.
  if (response.status === 204) {
    return undefined as T
  }

  const data = await response.json().catch(() => null)

  if (response.ok) {
    return data as T
  }

  throw new ApiError(response.status, errorMessage(response.status, data))
}

// --- Songs ---

export const listSongs = () => request<Song[]>('GET', '/songs')

export const getSong = (id: string) => request<Song>('GET', `/songs/${encodeURIComponent(id)}`)

export const createSong = (song: SongInput) => request<Song>('POST', '/songs', song)

export const updateSong = (id: string, song: SongInput) =>
  request<Song>('PUT', `/songs/${encodeURIComponent(id)}`, song)

export const deleteSong = (id: string) => request<void>('DELETE', `/songs/${encodeURIComponent(id)}`)

// --- Fragments ---

export const listFragments = () => request<Fragment[]>('GET', '/fragments')

export const getFragment = (id: string) => request<Fragment>('GET', `/fragments/${encodeURIComponent(id)}`)

export const createFragment = (fragment: FragmentInput) => request<Fragment>('POST', '/fragments', fragment)

export const updateFragment = (id: string, fragment: FragmentInput) =>
  request<Fragment>('PUT', `/fragments/${encodeURIComponent(id)}`, fragment)

export const deleteFragment = (id: string) => request<void>('DELETE', `/fragments/${encodeURIComponent(id)}`)

// --- Search, tags and random fragments ---

export type SearchQuery = { q?: string; scope?: Scope; tags?: string[] }

/** Songs and fragments matching every word in `q` and every tag in `tags`. */
export function search(query: SearchQuery) {
  const params = new URLSearchParams({ q: query.q ?? '', scope: query.scope ?? 'both' })

  for (const tag of query.tags ?? []) {
    params.append('tag', tag)
  }

  return request<SearchResults>('GET', `/search?${params}`)
}

/** Every tag in use, most used first. */
export const listTags = (scope: Scope = 'both') => request<TagCount[]>('GET', `/tags?scope=${scope}`)

export type RandomQuery = { count?: number; tag?: string; exclude?: string }

/** Random fragments. `exclude` is an ID to avoid, such as the fragment already on screen. */
export function randomFragments(query: RandomQuery = {}) {
  const params = new URLSearchParams({ count: String(query.count ?? 1) })

  if (query.tag) {
    params.set('tag', query.tag)
  }

  if (query.exclude) {
    params.set('exclude', query.exclude)
  }

  return request<Fragment[]>('GET', `/fragments/random?${params}`)
}
