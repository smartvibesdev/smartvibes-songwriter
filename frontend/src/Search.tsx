import { type FormEvent, useState } from 'react'
import { search, type SearchResults } from './api'
import { describeError } from './errors'

export function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResults | null>(null)
  const [searchedFor, setSearchedFor] = useState('')
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState('')

  async function submit(e: FormEvent) {
    e.preventDefault()

    const trimmed = query.trim()

    if (trimmed === '') {
      return
    }

    setError('')
    setSearching(true)

    try {
      setResults(await search(trimmed))
      setSearchedFor(trimmed)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSearching(false)
    }
  }

  const matchCount = results ? results.songs.length + results.fragments.length : 0

  return (
    <section>
      <h2>Search</h2>

      <form onSubmit={submit}>
        <input
          aria-label="Search your songs and fragments"
          placeholder="Search your songs and fragments"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          maxLength={100}
          size={40}
        />{' '}
        <button type="submit" disabled={searching}>
          Search
        </button>
      </form>

      {error && <p role="alert">{error}</p>}

      {results && matchCount === 0 && <p>No matches for "{searchedFor}".</p>}

      {results && results.songs.length > 0 && (
        <>
          <h3>Songs ({results.songs.length})</h3>

          <ul>
            {results.songs.map((song) => (
              <li key={song.id}>
                <strong>{song.title}</strong>
                <p>{song.body}</p>
              </li>
            ))}
          </ul>
        </>
      )}

      {results && results.fragments.length > 0 && (
        <>
          <h3>Fragments ({results.fragments.length})</h3>

          <ul>
            {results.fragments.map((fragment) => (
              <li key={fragment.id}>
                <p>{fragment.text}</p>

                {fragment.tags.length > 0 && <p>Tags: {fragment.tags.join(', ')}</p>}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
