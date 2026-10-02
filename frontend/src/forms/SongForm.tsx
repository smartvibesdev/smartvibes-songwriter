import { type FormEvent, useState } from 'react'
import { LIMITS, type SongInput } from '../api'
import { describeError } from '../errors'
import { formatTags, parseTags } from '../tags'
import { Button } from '../ui/Button'
import { ErrorText } from '../ui/ErrorText'
import { TextArea, TextInput } from '../ui/fields'

type SongFormProps = {
  initial: SongInput
  submitLabel: string
  /** Empty the form after a successful save (for the "add" form). */
  clearOnSuccess: boolean
  onSubmit: (input: SongInput) => Promise<void>
  onCancel?: () => void
  /** The label for the cancel button. Defaults to "Cancel". */
  cancelLabel?: string
}

export function SongForm({
  initial,
  submitLabel,
  clearOnSuccess,
  onSubmit,
  onCancel,
  cancelLabel = 'Cancel',
}: SongFormProps) {
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
            {cancelLabel}
          </Button>
        )}
      </div>

      {error && <ErrorText>{error}</ErrorText>}
    </form>
  )
}
