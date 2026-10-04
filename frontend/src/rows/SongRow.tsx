import type { Song } from '../api'
import { formatDate } from '../format'
import { hashTags } from '../tags'
import { Button } from '../ui/Button'

type SongRowProps = {
  song: Song
  /** Show a small "SONG" label, for lists that mix songs and fragments. */
  showKind?: boolean
  /** Open the song page to edit this song. */
  onEdit: () => void
  onDelete: () => void
}

/** One song in a list: title, the start of the lyrics, tags, date, and Edit and Delete. */
export function SongRow({ song, showKind, onEdit, onDelete }: SongRowProps) {
  return (
    <div className="flex flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:gap-6 sm:px-8 sm:py-5 lg:py-3.5">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        {/* Phones: "SONG – Title" on one line. Wider screens: the label above the title. */}
        <div className="flex flex-wrap items-baseline gap-x-2 sm:flex-col sm:items-start sm:gap-1">
          {showKind && (
            <p className="text-[11px] font-semibold tracking-[0.12em] text-primary-text uppercase">
              Song<span className="sm:hidden"> &ndash;</span>
            </p>
          )}

          <h2 className="font-display text-lg font-semibold sm:text-xl">{song.title}</h2>
        </div>

        {song.body && <p className="line-clamp-2 leading-snug whitespace-pre-line text-soft">{song.body}</p>}

        {song.tags.length > 0 && <p className="text-[13px] text-muted">{hashTags(song.tags)}</p>}
      </div>

      {/* Phones: the date at the left and the buttons at the right of one line. */}
      <div className="flex items-center justify-between gap-6 sm:contents">
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
    </div>
  )
}
