import { type FormEvent, useState } from 'react'
import { type FragmentInput, LIMITS } from '../api'
import { describeError } from '../errors'
import { formatTags, parseTags } from '../tags'
import { Button } from '../ui/Button'
import { ErrorText } from '../ui/ErrorText'

type FragmentFormProps = {
  initial: FragmentInput
  submitLabel: string
  /** Empty the form after a successful save (for the "add" form). */
  clearOnSuccess: boolean
  onSubmit: (input: FragmentInput) => Promise<void>
  onCancel?: () => void
  /** The label for the cancel button. Defaults to "Cancel". */
  cancelLabel?: string
}

export function FragmentForm({
  initial,
  submitLabel,
  clearOnSuccess,
  onSubmit,
  onCancel,
  cancelLabel = 'Cancel',
}: FragmentFormProps) {
  const [text, setText] = useState(initial.text)
  const [tagsText, setTagsText] = useState(formatTags(initial.tags))
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSaving(true)

    try {
      await onSubmit({ text, tags: parseTags(tagsText) })

      if (clearOnSuccess) {
        setText('')
        setTagsText('')
      }
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-5">
      <textarea
        aria-label="Fragment text"
        placeholder="A line, an image, an idea…"
        value={text}
        onChange={(e) => setText(e.target.value)}
        maxLength={LIMITS.fragmentText}
        rows={3}
        required
        className="w-full resize-none bg-transparent text-xl leading-relaxed text-foreground outline-none placeholder:text-muted"
      />

      <div className="flex flex-wrap items-center gap-4 border-t border-border pt-5">
        <input
          aria-label="Tags"
          placeholder="Tags, separated by commas"
          value={tagsText}
          onChange={(e) => setTagsText(e.target.value)}
          className="min-w-48 flex-1 bg-transparent text-foreground outline-none placeholder:text-muted"
        />

        {onCancel && (
          <Button variant="quiet" onClick={onCancel}>
            {cancelLabel}
          </Button>
        )}

        <Button type="submit" disabled={saving}>
          {submitLabel}
        </Button>
      </div>

      {error && <ErrorText>{error}</ErrorText>}
    </form>
  )
}
