import type { Song, SongInput } from '../api'
import { formatDate } from '../format'
import { SongForm } from '../forms/SongForm'
import { hashTags } from '../tags'
import { Button } from '../ui/Button'

type SongRowProps = {
  song: Song
  /** Show the form in place of the row. */
  editing: boolean
  /** Show a small "SONG" label, for lists that mix songs and fragments. */
  showKind?: boolean
  onEdit: () => void
  onCancelEdit: () => void
  onSave: (input: SongInput) => Promise<void>
  onDelete: () => void
}

/** One song in a list: title, the start of the lyrics, tags, date, and Edit and Delete. */
export function SongRow({ song, editing, showKind, onEdit, onCancelEdit, onSave, onDelete }: SongRowProps) {
  if (editing) {
    return (
      <div className="p-6 sm:px-8 sm:py-7">
        <SongForm initial={song} submitLabel="Save" clearOnSuccess={false} onSubmit={onSave} onCancel={onCancelEdit} />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3 px-6 py-5 sm:flex-row sm:items-center sm:gap-6 sm:px-8 lg:py-3.5">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        {showKind && <p className="text-[11px] font-semibold tracking-[0.12em] text-primary-text uppercase">Song</p>}

        <h2 className="font-display text-xl font-semibold">{song.title}</h2>

        {song.body && <p className="line-clamp-2 leading-snug whitespace-pre-line text-soft">{song.body}</p>}

        {song.tags.length > 0 && <p className="text-[13px] text-muted">{hashTags(song.tags)}</p>}
      </div>

      <p className="text-sm whitespace-nowrap text-muted">{formatDate(song.created_at)}</p>

      <div className="flex gap-4">
        <Button variant="link" className="text-sm" onClick={onEdit}>
          Edit
        </Button>

        <Button variant="quiet" className="text-sm" onClick={onDelete}>
          Delete
        </Button>
      </div>
    </div>
  )
}
