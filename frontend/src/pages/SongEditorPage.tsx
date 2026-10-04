import { type FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { LIMITS, type SongInput, getSong } from '../api'
import { describeError } from '../errors'
import { formatCount } from '../format'
import { formatTags, parseTags } from '../tags'
import { useAppState } from '../state/AppStateContext'
import { useLoaded } from '../useLoaded'
import { Button } from '../ui/Button'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { ErrorText } from '../ui/ErrorText'
import { TextInput } from '../ui/fields'
import { Spinner } from '../ui/Spinner'
import { TextEditor } from '../ui/TextEditor'

const BLANK_SONG: SongInput = { title: '', body: '', tags: [] }

/** The song page: a blank editor for `/songs/new`, or the saved song for `/songs/:id`. */
export function SongEditorPage() {
  const { id } = useParams()

  if (id === undefined) {
    return <SongEditor initial={BLANK_SONG} songId={null} />
  }

  return <SavedSong id={id} />
}

/** Loads one saved song, then shows it in the editor. */
function SavedSong({ id }: { id: string }) {
  const load = useCallback(() => getSong(id), [id])
  const { data: song, error } = useLoaded(load)

  if (song !== null) {
    return <SongEditor key={song.id} initial={song} songId={song.id} />
  }

  if (error) {
    return (
      <div className="flex flex-col gap-4">
        <ErrorText>{error}</ErrorText>

        <Link to="/" className="font-semibold text-primary-text hover:underline">
          Back to Home
        </Link>
      </div>
    )
  }

  return (
    <div className="flex justify-center py-16">
      <Spinner />
    </div>
  )
}

type SongEditorProps = {
  initial: SongInput
  /** The song being edited, or null for a new song. */
  songId: string | null
}

function SongEditor({ initial, songId }: SongEditorProps) {
  const navigate = useNavigate()
  const { songs, notebook } = useAppState()
  const [title, setTitle] = useState(initial.title)
  const [body, setBody] = useState(initial.body)
  const [tagsText, setTagsText] = useState(formatTags(initial.tags))
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [confirmingDiscard, setConfirmingDiscard] = useState(false)

  const hasChanges = title !== initial.title || body !== initial.body || tagsText !== formatTags(initial.tags)
  const canSave = title.trim().length > 0 && saving === false

  async function save() {
    if (canSave === false) {
      return
    }

    setError('')
    setSaving(true)

    try {
      const input = { title, body, tags: parseTags(tagsText) }

      if (songId === null) {
        await songs.create(input)
        notebook.showNewest()
      } else {
        await songs.update(songId, input)
      }

      navigate('/')
    } catch (err) {
      setError(describeError(err))
      setSaving(false)
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    save()
  }

  // Cmd+S or Ctrl+S saves from anywhere on the page. The listener always calls the latest `save`.
  const latestSave = useRef(save)

  useEffect(() => {
    latestSave.current = save
  })

  useEffect(() => {
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      const isSaveShortcut = event.key === 's' && (event.metaKey || event.ctrlKey)

      if (isSaveShortcut) {
        event.preventDefault()
        latestSave.current()
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  function cancel() {
    if (hasChanges) {
      setConfirmingDiscard(true)
    } else {
      navigate('/')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 lg:h-full lg:min-h-0">
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-display text-2xl font-semibold">{songId === null ? 'New song' : 'Edit song'}</h1>

        <div className="flex items-center gap-4">
          <Button variant="quiet" onClick={cancel}>
            Cancel
          </Button>

          <Button type="submit" disabled={canSave === false}>
            {saving ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </div>

      {error && <ErrorText>{error}</ErrorText>}

      <TextInput
        aria-label="Song title"
        placeholder="Title"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        maxLength={LIMITS.title}
        className="font-display text-xl font-semibold"
        required
      />

      <div className="h-[55vh] rounded-2xl border border-border bg-card focus-within:border-primary-text focus-within:ring-2 focus-within:ring-primary-text/30 lg:h-auto lg:min-h-0 lg:flex-1">
        <TextEditor
          initialValue={initial.body}
          onChange={setBody}
          label="Song lyrics"
          placeholderText="Lyrics"
          maxLength={LIMITS.songBody}
        />
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
        <TextInput
          aria-label="Tags"
          placeholder="Tags, separated by commas"
          value={tagsText}
          onChange={(event) => setTagsText(event.target.value)}
          className="sm:flex-1"
        />

        <p className="text-sm whitespace-nowrap text-muted sm:text-right">
          {formatCount(body.length)} / {formatCount(LIMITS.songBody)}
        </p>
      </div>

      <ConfirmDialog
        open={confirmingDiscard}
        title="Discard your changes?"
        description="What you typed on this page will be lost."
        confirmLabel="Discard"
        pending={false}
        onConfirm={() => navigate('/')}
        onCancel={() => setConfirmingDiscard(false)}
      />
    </form>
  )
}
