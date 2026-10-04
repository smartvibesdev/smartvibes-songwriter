import { LayoutGrid, X } from 'lucide-react'
import { type KeyboardEvent, useState } from 'react'
import type { TagCount } from '../api'
import { TagBrowser } from '../catalog/TagBrowser'
import { TAG_LIMITS, cleanTag } from '../tags'
import { toggleItem } from '../lists'
import { useAppState } from '../state/AppStateContext'
import { cx } from './cx'

type TagInputProps = {
  tags: string[]
  onChange: (tags: string[]) => void
  className?: string
}

const MAX_SUGGESTIONS = 8

/** The user's tags that are not chosen yet and contain what was typed, most used first. */
function pickSuggestions(allTags: TagCount[], chosen: string[], typed: string): string[] {
  const wanted = cleanTag(typed)

  return allTags
    .map(({ tag }) => tag)
    .filter((tag) => chosen.includes(tag) === false && tag.includes(wanted))
    .slice(0, MAX_SUGGESTIONS)
}

/** What the add box says: an invitation, or that no more tags fit. */
function placeholderFor(count: number): string {
  if (count >= TAG_LIMITS.count) {
    return 'Tag limit reached'
  }

  if (count === 0) {
    return 'Add tags'
  }

  return 'Add a tag'
}

/** Tags as chips (click to remove), an add box with suggestions from the user's own tags, and a browse box. */
export function TagInput({ tags, onChange, className }: TagInputProps) {
  const { homeTags } = useAppState()
  const [typed, setTyped] = useState('')
  const [focused, setFocused] = useState(false)
  const [browsing, setBrowsing] = useState(false)

  const isFull = tags.length >= TAG_LIMITS.count
  const suggestions = pickSuggestions(homeTags, tags, typed)
  const showSuggestions = focused && isFull === false && suggestions.length > 0

  function addTag(text: string) {
    const tag = cleanTag(text)

    if (tag.length > 0 && isFull === false && tags.includes(tag) === false) {
      onChange([...tags, tag])
    }

    setTyped('')
  }

  function removeLast() {
    onChange(tags.slice(0, -1))
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    const isAddKey = event.key === 'Enter' || event.key === ','

    if (isAddKey) {
      // Enter must not submit the surrounding form, and the comma must not be typed.
      event.preventDefault()
      addTag(typed)
    } else if (event.key === 'Backspace' && typed.length === 0) {
      removeLast()
    }
  }

  function handleChange(text: string) {
    // Pasting "love, rain" adds both tags.
    if (text.includes(',')) {
      text.split(',').forEach(addTag)

      return
    }

    setTyped(text)
  }

  return (
    <div className={cx('relative', className)}>
      <div className="flex flex-wrap items-center gap-2">
        {tags.map((tag) => (
          <button
            key={tag}
            type="button"
            aria-label={`Remove tag ${tag}`}
            onClick={() => onChange(toggleItem(tags, tag))}
            className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-primary bg-primary px-3 py-1 text-sm font-semibold text-primary-foreground"
          >
            {tag}
            <X size={14} aria-hidden="true" />
          </button>
        ))}

        <input
          aria-label="Add a tag"
          placeholder={placeholderFor(tags.length)}
          value={typed}
          disabled={isFull}
          maxLength={TAG_LIMITS.length + 1}
          onChange={(event) => handleChange(event.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => {
            setFocused(false)
            addTag(typed)
          }}
          className="min-w-28 flex-1 bg-transparent py-1 text-foreground outline-none placeholder:text-muted"
        />

        {homeTags.length > 0 && (
          <button
            type="button"
            aria-label={`Browse all ${homeTags.length} tags`}
            title={`Browse all ${homeTags.length} tags`}
            onClick={() => setBrowsing(true)}
            className="cursor-pointer p-1 text-muted hover:text-foreground"
          >
            <LayoutGrid size={20} aria-hidden="true" />
          </button>
        )}
      </div>

      {showSuggestions && (
        <div className="mt-2 flex flex-wrap gap-2">
          {suggestions.map((tag) => (
            <button
              key={tag}
              type="button"
              // Keep the box focused so the list does not vanish before the click lands.
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => addTag(tag)}
              className="cursor-pointer rounded-full border border-border bg-card px-3 py-1 text-sm text-soft hover:border-muted"
            >
              {tag}
            </button>
          ))}
        </div>
      )}

      <TagBrowser
        open={browsing}
        tags={homeTags}
        selected={tags}
        onToggle={(tag) => onChange(toggleItem(tags, tag))}
        onClose={() => setBrowsing(false)}
      />
    </div>
  )
}
