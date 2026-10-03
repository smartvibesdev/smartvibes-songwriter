import type { Fragment, FragmentInput } from '../api'
import { formatDate } from '../format'
import { FragmentForm } from '../forms/FragmentForm'
import { hashTags } from '../tags'
import { Button } from '../ui/Button'

type FragmentRowProps = {
  fragment: Fragment
  /** Show the form in place of the row. */
  editing: boolean
  /** Show a small "FRAGMENT" label, for lists that mix songs and fragments. */
  showKind?: boolean
  onEdit: () => void
  onCancelEdit: () => void
  onSave: (input: FragmentInput) => Promise<void>
  onDelete: () => void
}

/** One fragment in a list: its text, tags, date, and Edit and Delete. */
export function FragmentRow({ fragment, editing, showKind, onEdit, onCancelEdit, onSave, onDelete }: FragmentRowProps) {
  if (editing) {
    return (
      <div className="p-6 sm:px-8 sm:py-7">
        <FragmentForm
          initial={fragment}
          submitLabel="Save"
          clearOnSuccess={false}
          onSubmit={onSave}
          onCancel={onCancelEdit}
        />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:gap-6 sm:px-8 sm:py-5 lg:py-3.5">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        {showKind && <p className="text-[11px] font-semibold tracking-[0.12em] text-accent-text uppercase">Fragment</p>}

        <p className="text-lg leading-snug whitespace-pre-line">{fragment.text}</p>

        {fragment.tags.length > 0 && <p className="text-[13px] text-muted">{hashTags(fragment.tags)}</p>}
      </div>

      {/* Phones: the date at the left and the buttons at the right of one line. */}
      <div className="flex items-center justify-between gap-6 sm:contents">
        <p className="text-sm whitespace-nowrap text-muted">{formatDate(fragment.created_at)}</p>

        <div className="flex gap-4">
          <Button variant="link" className="text-sm" onClick={onEdit}>
            Edit
          </Button>

          <Button variant="quiet" className="text-sm" onClick={onDelete}>
            Delete
          </Button>
        </div>
      </div>
    </div>
  )
}
