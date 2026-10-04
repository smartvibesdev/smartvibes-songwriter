import type { Fragment, FragmentInput } from '../api'
import { formatDate } from '../format'
import { FragmentForm } from '../forms/FragmentForm'
import { hashTags } from '../tags'
import { Button } from '../ui/Button'
import { CARD, CARD_LINK } from './cardLink'

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

/** One fragment in a list: its text, tags, date, and Delete. The whole card opens it for editing. */
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
    <div
      className={`${CARD} flex flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:gap-6 sm:px-8 sm:py-5 lg:py-3.5`}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        {showKind && <p className="text-[11px] font-semibold tracking-[0.12em] text-accent-text uppercase">Fragment</p>}

        <button type="button" onClick={onEdit} className={`block w-full text-left ${CARD_LINK}`}>
          <span className="block text-lg leading-snug whitespace-pre-line">{fragment.text}</span>
        </button>

        {fragment.tags.length > 0 && <p className="text-[13px] text-muted">{hashTags(fragment.tags)}</p>}
      </div>

      {/* Phones: the date at the left and the buttons at the right of one line. */}
      <div className="flex items-center justify-between gap-6 sm:contents">
        <p className="text-sm whitespace-nowrap text-muted">{formatDate(fragment.created_at)}</p>

        <Button variant="quiet" className="relative z-10 text-sm" onClick={onDelete}>
          Delete
        </Button>
      </div>
    </div>
  )
}
