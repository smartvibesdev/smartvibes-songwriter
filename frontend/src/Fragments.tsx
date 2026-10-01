import { type FormEvent, useState } from 'react'
import { LIMITS, createFragment, deleteFragment, listFragments, updateFragment, type FragmentInput } from './api'
import { describeError } from './errors'
import { formatDate } from './format'
import { removeById, replaceById } from './lists'
import { useLoaded } from './useLoaded'

/** "love, rain" becomes ['love', 'rain']. The server also cleans tags up. */
function parseTags(tagsText: string): string[] {
  return tagsText
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)
}

type FragmentFormProps = {
  initial: FragmentInput
  submitLabel: string
  /** Empty the form after a successful save (for the "add" form). */
  clearOnSuccess: boolean
  onSubmit: (input: FragmentInput) => Promise<void>
  onCancel?: () => void
}

function FragmentForm({ initial, submitLabel, clearOnSuccess, onSubmit, onCancel }: FragmentFormProps) {
  const [text, setText] = useState(initial.text)
  const [tagsText, setTagsText] = useState(initial.tags.join(', '))
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
    <form onSubmit={submit}>
      <p>
        <textarea
          aria-label="Fragment text"
          placeholder="A line, an image, an idea..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={LIMITS.fragmentText}
          rows={3}
          cols={60}
          required
        />
      </p>

      <p>
        <input
          aria-label="Tags"
          placeholder="Tags, separated by commas"
          value={tagsText}
          onChange={(e) => setTagsText(e.target.value)}
          size={40}
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

export function Fragments() {
  const { data: fragments, setData: setFragments, error: loadError } = useLoaded(listFragments)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [actionError, setActionError] = useState('')

  async function handleCreate(input: FragmentInput) {
    const created = await createFragment(input)

    setFragments((current) => [created, ...(current ?? [])])
  }

  async function handleUpdate(id: string, input: FragmentInput) {
    const updated = await updateFragment(id, input)

    setFragments((current) => replaceById(current ?? [], updated))
    setEditingId(null)
  }

  async function handleDelete(id: string) {
    if (window.confirm('Delete this fragment? This cannot be undone.')) {
      setActionError('')

      try {
        await deleteFragment(id)
        setFragments((current) => removeById(current ?? [], id))
      } catch (err) {
        setActionError(describeError(err))
      }
    }
  }

  return (
    <section>
      <h2>Fragments</h2>

      <FragmentForm
        initial={{ text: '', tags: [] }}
        submitLabel="Add fragment"
        clearOnSuccess={true}
        onSubmit={handleCreate}
      />

      {loadError && <p role="alert">{loadError}</p>}
      {actionError && <p role="alert">{actionError}</p>}

      {fragments === null && loadError === '' && <p>Loading...</p>}

      {fragments && (
        <ul>
          {fragments.map((fragment) => (
            <li key={fragment.id}>
              {editingId === fragment.id ? (
                <FragmentForm
                  initial={fragment}
                  submitLabel="Save"
                  clearOnSuccess={false}
                  onSubmit={(input) => handleUpdate(fragment.id, input)}
                  onCancel={() => setEditingId(null)}
                />
              ) : (
                <>
                  <p>{fragment.text}</p>
                  <p>
                    {fragment.tags.length > 0 && <>Tags: {fragment.tags.join(', ')} &middot; </>}
                    Updated {formatDate(fragment.updated_at)}
                  </p>
                  <button type="button" onClick={() => setEditingId(fragment.id)}>
                    Edit
                  </button>{' '}
                  <button type="button" onClick={() => handleDelete(fragment.id)}>
                    Delete
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      {fragments?.length === 0 && <p>No fragments yet. Add your first one above.</p>}
    </section>
  )
}
