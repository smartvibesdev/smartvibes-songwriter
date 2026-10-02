import { ArrowLeft, ArrowRight } from 'lucide-react'
import type { SortOrder } from '../api'
import { formatCount } from '../format'
import { Button } from '../ui/Button'

type PagerProps = {
  page: number
  pages: number
  sort: SortOrder
  onPage: (number: number) => void
}

/** Which page number is the newer side and which is the older side, for the current order. */
function neighbours(page: number, sort: SortOrder) {
  if (sort === 'newest') {
    return { newer: page - 1, older: page + 1 }
  }

  return { newer: page + 1, older: page - 1 }
}

/** Newer and older arrow buttons with "Page X of Y", for the bottom of a list. */
export function Pager({ page, pages, sort, onPage }: PagerProps) {
  const { newer, older } = neighbours(page, sort)

  return (
    <nav aria-label="Pages" className="flex items-center gap-5">
      <Button
        variant="outline"
        className="px-4"
        aria-label="Newer page"
        onClick={() => onPage(newer)}
        disabled={newer < 1 || newer > pages}
      >
        <ArrowLeft size={18} />
      </Button>

      <span className="text-[15px] text-muted">
        Page {formatCount(page)} of {formatCount(pages)}
      </span>

      <Button
        variant="outline"
        className="px-4"
        aria-label="Older page"
        onClick={() => onPage(older)}
        disabled={older < 1 || older > pages}
      >
        <ArrowRight size={18} />
      </Button>
    </nav>
  )
}
