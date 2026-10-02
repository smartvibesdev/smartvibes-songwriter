import { Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { type Scope, type SearchResults, type TagCount, search } from '../api'
import { describeError } from '../errors'
import { formatDate } from '../format'
import { toggleItem } from '../lists'
import { hashTags } from '../tags'
import { Card } from '../ui/Card'
import { cx } from '../ui/cx'

const SCOPES: { id: Scope; label: string }[] = [
  { id: 'both', label: 'Both' },
  { id: 'songs', label: 'Songs' },
  { id: 'fragments', label: 'Fragments' },
]

// How many tag chips to show, and how long to wait after typing before searching.
const MAX_TAG_CHIPS = 12
const TYPING_DELAY_MS = 300

type SearchPanelProps = {
  /** All the user's tags, most used first. */
  tags: TagCount[]
}

/** Search by words, tags and scope. Results appear as you type. */
export function SearchPanel({ tags }: SearchPanelProps) {
  const [query, setQuery] = useState('')
  const [scope, setScope] = useState<Scope>('both')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [results, setResults] = useState<SearchResults | null>(null)
  const [error, setError] = useState('')

  const words = query.trim()
  const hasCriteria = Boolean(words) || selectedTags.length > 0

  useEffect(() => {
    let active = true
    let timer: ReturnType<typeof setTimeout> | undefined

    if (hasCriteria) {
      timer = setTimeout(async () => {
        try {
          const found = await search({ q: words, scope, tags: selectedTags })

          if (active) {
            setResults(found)
            setError('')
          }
        } catch (err) {
          if (active) {
            setError(describeError(err))
          }
        }
      }, TYPING_DELAY_MS)
    }

    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [hasCriteria, words, scope, selectedTags])

  function renderResults() {
    if (hasCriteria === false) {
      return <p className="text-muted">Type a word, or pick a tag, to search.</p>
    }

    if (error) {
      return <p role="alert">{error}</p>
    }

    if (results === null) {
      return <p className="text-muted">Searching&hellip;</p>
    }

    if (results.songs.length + results.fragments.length === 0) {
      return <p className="text-muted">No matches.</p>
    }

    return (
      <div className="grid gap-7 md:grid-cols-2">
        {results.songs.map((song) => (
          <Card key={song.id} className="flex flex-col gap-3.5">
            <p className="text-xs font-semibold tracking-[0.12em] text-primary-text uppercase">Song</p>
            <h3 className="font-display text-2xl font-semibold">{song.title}</h3>
            {song.body && <p className="leading-relaxed whitespace-pre-line text-soft">{song.body.slice(0, 160)}</p>}
            <p className="text-sm text-muted">
              {hashTags(song.tags)} {song.tags.length > 0 && <>&middot; </>}Updated {formatDate(song.updated_at)}
            </p>
          </Card>
        ))}

        {results.fragments.map((fragment) => (
          <Card key={fragment.id} className="flex flex-col gap-3.5">
            <p className="text-xs font-semibold tracking-[0.12em] text-accent-text uppercase">Fragment</p>
            <p className="text-xl leading-relaxed">{fragment.text}</p>
            <p className="text-sm text-muted">
              {hashTags(fragment.tags)} {fragment.tags.length > 0 && <>&middot; </>}Updated{' '}
              {formatDate(fragment.updated_at)}
            </p>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <section className="flex flex-col gap-6">
      <div className="flex items-center gap-3.5 rounded-[1.25rem] border border-border bg-card px-6 shadow-card focus-within:border-primary-text focus-within:ring-2 focus-within:ring-primary-text/30">
        <Search size={20} className="text-muted" aria-hidden="true" />

        <input
          aria-label="Search your songs and fragments"
          placeholder="Search by word&hellip;"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          maxLength={100}
          className="w-full bg-transparent py-5 text-lg text-foreground outline-none placeholder:text-muted"
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex gap-7" role="group" aria-label="Search in">
          {SCOPES.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              aria-pressed={scope === id}
              onClick={() => setScope(id)}
              className={cx(
                'cursor-pointer border-b-2 pb-1 text-[15px] transition',
                scope === id ? 'border-accent font-semibold text-foreground' : 'border-transparent text-muted',
              )}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap gap-2.5" role="group" aria-label="Filter by tag">
          {tags.slice(0, MAX_TAG_CHIPS).map(({ tag }) => (
            <button
              key={tag}
              type="button"
              aria-pressed={selectedTags.includes(tag)}
              onClick={() => setSelectedTags((current) => toggleItem(current, tag))}
              className={cx(
                'cursor-pointer rounded-full border px-4 py-1.5 text-sm transition',
                selectedTags.includes(tag)
                  ? 'border-primary bg-primary font-semibold text-primary-foreground'
                  : 'border-border bg-card text-soft hover:border-muted',
              )}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      {renderResults()}
    </section>
  )
}
