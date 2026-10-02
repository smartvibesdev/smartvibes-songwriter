import type { ReactNode } from 'react'
import type { Page, SortOrder } from '../api'
import { formatCount } from '../format'
import { Button } from '../ui/Button'
import { ErrorText } from '../ui/ErrorText'
import { Spinner } from '../ui/Spinner'
import { Pager } from './Pager'

type CatalogListProps<Item extends { id: string }> = {
  /** "fragment" or "song", for the messages. */
  noun: string
  /** What to say when the list is empty and no filter is on. */
  emptyMessage?: string
  page: Page<Item> | null
  sort: SortOrder
  hasFilters: boolean
  /** True while a new page is on its way; the current rows are dimmed and a spinner shows. */
  loading: boolean
  loadError: string
  actionError: string
  onPage: (number: number) => void
  onClearFilters: () => void
  /** Draws one row. */
  renderRow: (item: Item) => ReactNode
}

/** The summary line, the rows, and the pager, shared by the Songs and Fragments pages. */
export function CatalogList<Item extends { id: string }>(props: CatalogListProps<Item>) {
  const {
    noun,
    emptyMessage,
    page,
    sort,
    hasFilters,
    loading,
    loadError,
    actionError,
    onPage,
    onClearFilters,
    renderRow,
  } = props

  if (page === null) {
    if (loadError) {
      return <ErrorText>{loadError}</ErrorText>
    }

    return <p className="text-muted">Loading…</p>
  }

  const firstShown = (page.page - 1) * page.page_size + 1
  const lastShown = Math.min(page.page * page.page_size, page.total)
  const busyClasses = loading ? 'opacity-60' : 'opacity-100'
  // The spinner waits a moment, so a fast answer never flashes it.
  const spinnerClasses = loading ? 'opacity-100 delay-200' : 'opacity-0'

  return (
    <div className="relative flex flex-col gap-6 lg:min-h-0 lg:flex-1 lg:gap-4" aria-busy={loading}>
      <Spinner
        className={`pointer-events-none absolute top-1/3 left-1/2 z-10 -translate-x-1/2 transition-opacity duration-200 ${spinnerClasses}`}
      />
      {loadError && <ErrorText>{loadError}</ErrorText>}
      {actionError && <ErrorText>{actionError}</ErrorText>}

      {page.items.length === 0 && (
        <p className="py-6 text-muted">
          {hasFilters ? (
            <>
              Nothing matches. Try fewer filters, or{' '}
              <Button variant="link" onClick={onClearFilters}>
                clear them
              </Button>
              .
            </>
          ) : (
            (emptyMessage ?? `No ${noun}s yet. Add your first one with the button above.`)
          )}
        </p>
      )}

      {page.items.length > 0 && (
        <ul
          className={`overflow-hidden rounded-3xl border border-border bg-card shadow-card transition-opacity lg:min-h-0 lg:flex-1 lg:overflow-y-auto ${busyClasses}`}
        >
          {page.items.map((item) => (
            <li key={item.id} className="border-b border-border last:border-b-0">
              {renderRow(item)}
            </li>
          ))}
        </ul>
      )}

      {/* The pager sits in the middle; the count is at the right (stacked and centered on a phone). */}
      <div className="grid items-center justify-items-center gap-y-3 lg:grid-cols-[1fr_auto_1fr]">
        <span className="hidden lg:block" />

        {page.pages > 1 ? <Pager page={page.page} pages={page.pages} sort={sort} onPage={onPage} /> : <span />}

        <p className="text-[15px] text-muted lg:justify-self-end lg:pr-4">
          {page.total > 0 && (
            <>
              Showing{' '}
              <strong className="font-semibold text-foreground">
                {formatCount(firstShown)}&ndash;{formatCount(lastShown)}
              </strong>{' '}
              of <strong className="font-semibold text-foreground">{formatCount(page.total)}</strong>
              {hasFilters && ' matching'}
            </>
          )}

          {hasFilters && page.total > 0 && (
            <>
              {' · '}
              <Button variant="link" className="text-[15px]" onClick={onClearFilters}>
                Clear filters
              </Button>
            </>
          )}
        </p>
      </div>
    </div>
  )
}
