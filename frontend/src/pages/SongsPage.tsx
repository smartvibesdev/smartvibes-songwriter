import { type FormEvent, useState } from 'react'
import { LIMITS, type Song, type SongInput, createSong, deleteSong, listSongs, updateSong } from '../api'
import { describeError } from '../errors'
import { formatDate } from '../format'
import { formatTags, hashTags, parseTags } from '../tags'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { ErrorText } from '../ui/ErrorText'
import { TextArea, TextInput } from '../ui/fields'
import { PageHeading } from '../ui/PageHeading'
import { useCrudList } from '../useCrudList'

const SONG_API = { list: listSongs, create: createSong, update: updateSong, remove: deleteSong }

const EMPTY_SONG: SongInput = { title: '', body: '', tags: [] }

const PREVIEW_LENGTH = 140

/** The start of a song's lyrics, for the list. */
function preview(body: string): string {
  if (body.length > PREVIEW_LENGTH) {
    return `${body.slice(0, PREVIEW_LENGTH)}…`
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
  const [tagsText, setTagsText] = useState(formatTags(initial.tags))
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSaving(true)

    try {
      await onSubmit({ title, body, tags: parseTags(tagsText) })

      if (clearOnSuccess) {
        setTitle('')
        setBody('')
        setTagsText('')
      }
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <TextInput
        aria-label="Song title"
        placeholder="Title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        maxLength={LIMITS.title}
        required
      />

      <TextArea
        aria-label="Song lyrics"
        placeholder="Lyrics"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        maxLength={LIMITS.songBody}
        rows={10}
      />

      <TextInput
        aria-label="Tags"
        placeholder="Tags, separated by commas"
        value={tagsText}
        onChange={(e) => setTagsText(e.target.value)}
      />

      <div className="flex items-center gap-4">
        <Button type="submit" disabled={saving}>
          {submitLabel}
        </Button>

        {onCancel && (
          <Button variant="quiet" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>

      {error && <ErrorText>{error}</ErrorText>}
    </form>
  )
}

export function SongsPage() {
  const crud = useCrudList<Song, SongInput>(SONG_API)
  const songs = crud.items

  return (
    <div className="flex flex-col gap-10">
      <PageHeading title="Songs" subtitle="Your finished and unfinished songs, all in one place." />

      <Card>
        <SongForm initial={EMPTY_SONG} submitLabel="Add song" clearOnSuccess={true} onSubmit={crud.create} />
      </Card>

      {crud.loadError && <ErrorText>{crud.loadError}</ErrorText>}
      {crud.actionError && <ErrorText>{crud.actionError}</ErrorText>}

      {songs === null && crud.loadError === '' && <p className="text-muted">Loading…</p>}
      {songs?.length === 0 && <p className="text-muted">No songs yet. Add your first one above.</p>}

      <ul className="flex flex-col gap-5">
        {songs?.map((song) => (
          <li key={song.id}>
            <Card>
              {crud.editingId === song.id ? (
                <SongForm
                  initial={song}
                  submitLabel="Save"
                  clearOnSuccess={false}
                  onSubmit={(input) => crud.update(song.id, input)}
                  onCancel={() => crud.setEditingId(null)}
                />
              ) : (
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-5">
                  <div className="flex min-w-0 flex-1 flex-col gap-3">
                    <h2 className="font-display text-2xl font-semibold">{song.title}</h2>

                    {song.body && <p className="leading-relaxed whitespace-pre-line text-soft">{preview(song.body)}</p>}

                    <p className="text-sm text-muted">
                      {hashTags(song.tags)} {song.tags.length > 0 && <>&middot; </>}Updated{' '}
                      {formatDate(song.updated_at)}
                    </p>
                  </div>

                  <div className="flex gap-5">
                    <Button variant="link" onClick={() => crud.setEditingId(song.id)}>
                      Edit
                    </Button>

                    <Button variant="quiet" onClick={() => crud.setDeletingId(song.id)}>
                      Delete
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          </li>
        ))}
      </ul>

      <ConfirmDialog
        open={Boolean(crud.deletingId)}
        title="Delete this song?"
        description="It will be removed for good. This can't be undone."
        confirmLabel="Delete"
        pending={crud.deleting}
        onConfirm={crud.confirmDelete}
        onCancel={() => crud.setDeletingId(null)}
      />
    </div>
  )
}
