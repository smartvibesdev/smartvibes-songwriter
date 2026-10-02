import { X } from 'lucide-react'
import { type KeyboardEvent, useState } from 'react'
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
}

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
      <SearchBox
        value={props.searchText}
        onChange={props.onSearchText}
        label={props.placeholder}
        placeholder={props.placeholder}
      />

      <div className="flex flex-wrap items-center justify-between gap-x-8 gap-y-3">
        <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
          <label className="flex items-center gap-2.5">
            <FieldLabel>Year</FieldLabel>

            <Select
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
          <div className="flex flex-wrap items-center gap-3">
            <FieldLabel className="-mr-1">Tags</FieldLabel>

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
                onClick={() => setAddingTag(true)}
                className="cursor-pointer rounded-full border border-dashed border-muted/60 px-3.5 py-1.5 text-sm font-medium text-soft hover:border-muted"
              >
                + Add tag
              </button>
            )}

            {allTags.length > 0 && (
              <Button variant="link" className="text-sm" onClick={() => setBrowsing(true)}>
                Browse all {allTags.length} tags
              </Button>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          {props.scope && props.onScope && (
            <label className="flex items-center gap-2.5">
              <FieldLabel>Show</FieldLabel>

              <Select value={props.scope} onChange={(e) => props.onScope?.(e.target.value as Scope)}>
                <option value="both">All</option>
                <option value="fragments">Fragments</option>
                <option value="songs">Songs</option>
              </Select>
            </label>
          )}

          <label className="flex items-center gap-2.5">
            <FieldLabel>Sort</FieldLabel>

            <Select value={props.sort} onChange={(e) => props.onSort(e.target.value as SortOrder)}>
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
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
