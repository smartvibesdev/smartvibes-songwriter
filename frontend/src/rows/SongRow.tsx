import { Link } from 'react-router'
import type { Song } from '../api'
import { formatDate } from '../format'
import { hashTags } from '../tags'
import { Button } from '../ui/Button'
import { CARD, CARD_LINK } from './cardLink'

type SongRowProps = {
  song: Song
  /** Show a small "SONG" label, for lists that mix songs and fragments. */
  showKind?: boolean
  /** Where the card goes when clicked: the song page. */
  href: string
  onDelete: () => void
}

/** One song in a list: title, the start of the lyrics, tags, date, and Delete. The whole card opens the song. */
export function SongRow({ song, showKind, href, onDelete }: SongRowProps) {
  return (
    <div
      className={`${CARD} flex flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:gap-6 sm:px-8 sm:py-5 lg:py-3.5`}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        {/* Phones: "SONG – Title" on one line. Wider screens: the label above the title. */}
        <div className="flex flex-wrap items-baseline gap-x-2 sm:flex-col sm:items-start sm:gap-1">
          {showKind && (
            <p className="text-[11px] font-semibold tracking-[0.12em] text-primary-text uppercase">
              Song<span className="sm:hidden"> &ndash;</span>
            </p>
          )}

          <h2 className="font-display text-lg font-semibold sm:text-xl">
            <Link to={href} className={CARD_LINK}>
              {song.title}
            </Link>
          </h2>
        </div>

        {song.body && <p className="line-clamp-2 leading-snug whitespace-pre-line text-soft">{song.body}</p>}

        {song.tags.length > 0 && <p className="text-[13px] text-muted">{hashTags(song.tags)}</p>}
      </div>

      {/* Phones: the date at the left and the buttons at the right of one line. */}
      <div className="flex items-center justify-between gap-6 sm:contents">
        <p className="text-sm whitespace-nowrap text-muted">{formatDate(song.created_at)}</p>

        <Button variant="quiet" className="relative z-10 text-sm" onClick={onDelete}>
          Delete
        </Button>
      </div>
    </div>
  )
}
