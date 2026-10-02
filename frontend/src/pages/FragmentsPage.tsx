import { type FormEvent, useState } from 'react'
import {
  type Fragment,
  type FragmentInput,
  LIMITS,
  createFragment,
  deleteFragment,
  listFragments,
  updateFragment,
} from '../api'
import { describeError } from '../errors'
import { formatDate } from '../format'
import { formatTags, hashTags, parseTags } from '../tags'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { ErrorText } from '../ui/ErrorText'
import { PageHeading } from '../ui/PageHeading'
import { useCrudList } from '../useCrudList'

const FRAGMENT_API = { list: listFragments, create: createFragment, update: updateFragment, remove: deleteFragment }

const EMPTY_FRAGMENT: FragmentInput = { text: '', tags: [] }

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
            Cancel
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

export function FragmentsPage() {
  const crud = useCrudList<Fragment, FragmentInput>(FRAGMENT_API)
  const fragments = crud.items

  return (
    <div className="flex flex-col gap-10">
      <PageHeading title="Fragments" subtitle="Half-lines, images and ideas, saved before they get away." />

      <Card>
        <FragmentForm
          initial={EMPTY_FRAGMENT}
          submitLabel="Add fragment"
          clearOnSuccess={true}
          onSubmit={crud.create}
        />
      </Card>

      {crud.loadError && <ErrorText>{crud.loadError}</ErrorText>}
      {crud.actionError && <ErrorText>{crud.actionError}</ErrorText>}

      {fragments === null && crud.loadError === '' && <p className="text-muted">Loading…</p>}
      {fragments?.length === 0 && <p className="text-muted">No fragments yet. Add your first one above.</p>}

      <ul className="flex flex-col gap-5">
        {fragments?.map((fragment) => (
          <li key={fragment.id}>
            <Card className="p-6 sm:px-8 sm:py-7">
              {crud.editingId === fragment.id ? (
                <FragmentForm
                  initial={fragment}
                  submitLabel="Save"
                  clearOnSuccess={false}
                  onSubmit={(input) => crud.update(fragment.id, input)}
                  onCancel={() => crud.setEditingId(null)}
                />
              ) : (
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between sm:gap-5">
                  <div className="flex min-w-0 flex-1 flex-col gap-2">
                    <p className="text-xl leading-relaxed whitespace-pre-line">{fragment.text}</p>

                    <p className="text-sm text-muted">
                      {hashTags(fragment.tags)} {fragment.tags.length > 0 && <>&middot; </>}Updated{' '}
                      {formatDate(fragment.updated_at)}
                    </p>
                  </div>

                  <div className="flex gap-5">
                    <Button variant="link" onClick={() => crud.setEditingId(fragment.id)}>
                      Edit
                    </Button>

                    <Button variant="quiet" onClick={() => crud.setDeletingId(fragment.id)}>
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
        title="Delete this fragment?"
        description="It will be removed for good. This can't be undone."
        confirmLabel="Delete"
        pending={crud.deleting}
        onConfirm={crud.confirmDelete}
        onCancel={() => crud.setDeletingId(null)}
      />
    </div>
  )
}
