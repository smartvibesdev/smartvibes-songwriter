import { LayoutGrid, Plus, X } from 'lucide-react'
import { type KeyboardEvent, type ReactNode, useState } from 'react'
import type { Scope, SortOrder, TagCount, YearCount } from '../api'
import { Button } from '../ui/Button'
import { FieldLabel } from '../ui/FieldLabel'
import { SearchBox } from '../ui/SearchBox'
import { Select } from '../ui/Select'
import { TagBrowser } from './TagBrowser'

type CatalogToolbarProps = {
  placeholder: string
  searchText: string
  onSearchText: (text: string) => void
  /** Every tag the user has used, most used first. */
  allTags: TagCount[]
  selectedTags: string[]
  onToggleTag: (tag: string) => void
  /** Years that have matches, newest first. */
  years: YearCount[]
  year: number | null
  onYear: (year: number | null) => void
  sort: SortOrder
  onSort: (sort: SortOrder) => void
  /** Only for the mixed list on Home: which kinds to show. */
  scope?: Scope
  onScope?: (scope: Scope) => void
  /** A button shown beside the search box on phones (wider screens place it elsewhere). */
  phoneAction?: ReactNode
}

// On phones the four labels (Year, Tags, Show, Sort) are equally wide, so the controls line up in both columns.
const LABEL_WIDTH = 'w-10 sm:w-auto'

// Year, Show and Sort are all this wide, so the row looks even.
const SELECT_WIDTH = 'w-28'

/** The search box, tag filter, year selector and sort choice above a list. */
export function CatalogToolbar(props: CatalogToolbarProps) {
  const { allTags, selectedTags, onToggleTag, years, year, onYear } = props
  const [addingTag, setAddingTag] = useState(false)
  const [tagText, setTagText] = useState('')
  const [browsing, setBrowsing] = useState(false)

  // The years that have matches, newest first. Keep the chosen year listed even if the
  // current words or tags leave it with no matches, so the menu still shows what is chosen.
  const yearChoices = years.map((entry) => entry.year)

  if (year && yearChoices.includes(year) === false) {
    yearChoices.push(year)
    yearChoices.sort((a, b) => b - a)
  }

  const suggestions = allTags.filter(({ tag }) => selectedTags.includes(tag) === false)

  function handleTagKey(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') {
      event.preventDefault()

      const wanted = tagText.trim().toLowerCase()

      if (suggestions.some(({ tag }) => tag === wanted)) {
        onToggleTag(wanted)
        setTagText('')
        setAddingTag(false)
      }
    }

    if (event.key === 'Escape') {
      setTagText('')
      setAddingTag(false)
    }
  }

  return (
    // The search box has its own row; tags, year and sort share the row under it.
    <div className="flex flex-col gap-4 lg:gap-3">
      <div className="flex items-center gap-3">
        <div className="min-w-0 flex-1">
          <SearchBox
            value={props.searchText}
            onChange={props.onSearchText}
            label={props.placeholder}
            placeholder={props.placeholder}
          />
        </div>

        {props.phoneAction && <div className="shrink-0 sm:hidden">{props.phoneAction}</div>}
      </div>

      {/* Phones: a 2x2 grid (year, tags / show, sort). Wider screens: one wrapping row. */}
      <div className="grid grid-cols-2 items-center gap-x-4 gap-y-3 sm:flex sm:flex-wrap sm:justify-between sm:gap-x-8">
        <div className="contents sm:flex sm:flex-wrap sm:items-center sm:gap-x-8 sm:gap-y-3">
          <label className="flex items-center gap-2.5">
            <FieldLabel className={LABEL_WIDTH}>Year</FieldLabel>

            <Select
              className={SELECT_WIDTH}
              value={year === null ? '' : String(year)}
              onChange={(e) => onYear(e.target.value === '' ? null : Number(e.target.value))}
            >
              <option value="">All</option>
              {yearChoices.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </Select>
          </label>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-2 sm:gap-3">
            <FieldLabel className={`${LABEL_WIDTH} sm:-mr-1`}>Tags</FieldLabel>

            {selectedTags.map((tag) => (
              <button
                key={tag}
                type="button"
                aria-label={`Remove tag ${tag}`}
                onClick={() => onToggleTag(tag)}
                className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-primary bg-primary px-3.5 py-1.5 text-sm font-semibold text-primary-foreground"
              >
                {tag}
                <X size={14} aria-hidden="true" />
              </button>
            ))}

            {addingTag ? (
              <>
                <input
                  autoFocus
                  aria-label="Add a tag filter"
                  list="tag-suggestions"
                  placeholder="Type a tag, press Enter"
                  value={tagText}
                  onChange={(e) => setTagText(e.target.value)}
                  onKeyDown={handleTagKey}
                  className="rounded-full border border-border bg-card px-4 py-1.5 text-sm text-foreground outline-none focus:border-primary-text"
                />

                <datalist id="tag-suggestions">
                  {suggestions.slice(0, 50).map(({ tag }) => (
                    <option key={tag} value={tag} />
                  ))}
                </datalist>
              </>
            ) : (
              <button
                type="button"
                aria-label="Add a tag filter"
                onClick={() => setAddingTag(true)}
                className="inline-flex cursor-pointer items-center gap-1 rounded-full border border-dashed border-muted/60 px-2.5 py-1.5 text-sm font-medium text-soft hover:border-muted sm:px-3.5"
              >
                <Plus size={16} aria-hidden="true" />
                <span className="hidden sm:inline">Add</span>
              </button>
            )}

            {allTags.length > 0 && (
              <Button
                variant="link"
                className="text-sm"
                aria-label={`Browse all ${allTags.length} tags`}
                title={`Browse all ${allTags.length} tags`}
                onClick={() => setBrowsing(true)}
              >
                <LayoutGrid size={20} aria-hidden="true" className="sm:hidden" />
                <span className="hidden sm:inline">Browse</span>
              </Button>
            )}
          </div>
        </div>

        <div className="contents sm:flex sm:flex-wrap sm:items-center sm:gap-x-6 sm:gap-y-3">
          {props.scope && props.onScope && (
            <label className="flex items-center gap-2.5">
              <FieldLabel className={LABEL_WIDTH}>Show</FieldLabel>

              <Select
                className={SELECT_WIDTH}
                value={props.scope}
                onChange={(e) => props.onScope?.(e.target.value as Scope)}
              >
                <option value="both">All</option>
                <option value="fragments">Fragments</option>
                <option value="songs">Songs</option>
              </Select>
            </label>
          )}

          <label className="flex items-center gap-2.5">
            <FieldLabel className={LABEL_WIDTH}>Sort</FieldLabel>

            <Select
              className={SELECT_WIDTH}
              value={props.sort}
              onChange={(e) => props.onSort(e.target.value as SortOrder)}
            >
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
            </Select>
          </label>
        </div>
      </div>

      <TagBrowser
        open={browsing}
        tags={allTags}
        selected={selectedTags}
        onToggle={onToggleTag}
        onClose={() => setBrowsing(false)}
      />
    </div>
  )
}
