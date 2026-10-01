import { type FormEvent, useState } from 'react'
import { LIMITS, createSong, deleteSong, listSongs, updateSong, type SongInput } from './api'
import { describeError } from './errors'
import { formatDate } from './format'
import { removeById, replaceById } from './lists'
import { useLoaded } from './useLoaded'

const PREVIEW_LENGTH = 100

/** The start of a song's body, for the list. */
function preview(body: string): string {
  if (body.length > PREVIEW_LENGTH) {
    return `${body.slice(0, PREVIEW_LENGTH)}...`
  }

  return body
}

type SongFormProps = {
  initial: SongInput
  submitLabel: string
  /** Empty the form after a successful save (for the "add" form). */
  clearOnSuccess: boolean
  onSubmit: (input: SongInput) => Promise<void>
  onCancel?: () => void
}

function SongForm({ initial, submitLabel, clearOnSuccess, onSubmit, onCancel }: SongFormProps) {
  const [title, setTitle] = useState(initial.title)
  const [body, setBody] = useState(initial.body)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSaving(true)

    try {
      await onSubmit({ title, body })

      if (clearOnSuccess) {
        setTitle('')
        setBody('')
      }
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit}>
      <p>
        <input
          aria-label="Song title"
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={LIMITS.title}
          size={40}
          required
        />
      </p>

      <p>
        <textarea
          aria-label="Song lyrics"
          placeholder="Lyrics"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          maxLength={LIMITS.songBody}
          rows={12}
          cols={60}
        />
      </p>

      <button type="submit" disabled={saving}>
        {submitLabel}
      </button>

      {onCancel && (
        <>
          {' '}
          <button type="button" onClick={onCancel}>
            Cancel
          </button>
        </>
      )}

      {error && <p role="alert">{error}</p>}
    </form>
  )
}

export function Songs() {
  const { data: songs, setData: setSongs, error: loadError } = useLoaded(listSongs)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [actionError, setActionError] = useState('')

  async function handleCreate(input: SongInput) {
    const created = await createSong(input)

    setSongs((current) => [created, ...(current ?? [])])
  }

  async function handleUpdate(id: string, input: SongInput) {
    const updated = await updateSong(id, input)

    setSongs((current) => replaceById(current ?? [], updated))
    setEditingId(null)
  }

  async function handleDelete(id: string) {
    if (window.confirm('Delete this song? This cannot be undone.')) {
      setActionError('')

      try {
        await deleteSong(id)
        setSongs((current) => removeById(current ?? [], id))
      } catch (err) {
        setActionError(describeError(err))
      }
    }
  }

  return (
    <section>
      <h2>Songs</h2>

      <SongForm
        initial={{ title: '', body: '' }}
        submitLabel="Add song"
        clearOnSuccess={true}
        onSubmit={handleCreate}
      />

      {loadError && <p role="alert">{loadError}</p>}
      {actionError && <p role="alert">{actionError}</p>}

      {songs === null && loadError === '' && <p>Loading...</p>}

      {songs && (
        <ul>
          {songs.map((song) => (
            <li key={song.id}>
              {editingId === song.id ? (
                <SongForm
                  initial={song}
                  submitLabel="Save"
                  clearOnSuccess={false}
                  onSubmit={(input) => handleUpdate(song.id, input)}
                  onCancel={() => setEditingId(null)}
                />
              ) : (
                <>
                  <h3>{song.title}</h3>
                  <p>{preview(song.body)}</p>
                  <p>Updated {formatDate(song.updated_at)}</p>
                  <button type="button" onClick={() => setEditingId(song.id)}>
                    Edit
                  </button>{' '}
                  <button type="button" onClick={() => handleDelete(song.id)}>
                    Delete
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      {songs?.length === 0 && <p>No songs yet. Add your first one above.</p>}
    </section>
  )
}
