import * as Dialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { useState } from 'react'
import type { TagCount } from '../api'
import { formatCount } from '../format'
import { Button } from '../ui/Button'
import { cx } from '../ui/cx'
import { TextInput } from '../ui/fields'

type TagBrowserProps = {
  open: boolean
  tags: TagCount[]
  selected: string[]
  onToggle: (tag: string) => void
  onClose: () => void
}

/** A box listing every tag with its count, with a filter box, for when there are too many for chips. */
export function TagBrowser({ open, tags, selected, onToggle, onClose }: TagBrowserProps) {
  const [filter, setFilter] = useState('')
  const wanted = filter.trim().toLowerCase()
  const shown = tags.filter(({ tag }) => tag.includes(wanted))

  function handleOpenChange(next: boolean) {
    if (next === false) {
      onClose()
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={handleOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-[#0f1630]/50" />

        <Dialog.Content
          aria-describedby={undefined}
          className="fixed top-1/2 left-1/2 z-50 flex max-h-[85vh] w-[calc(100%-2rem)] max-w-xl -translate-x-1/2 -translate-y-1/2 flex-col gap-5 rounded-3xl border border-border bg-card p-8 shadow-2xl"
        >
          <div className="flex items-center justify-between">
            <Dialog.Title className="font-display text-2xl font-semibold">
              All tags ({formatCount(tags.length)})
            </Dialog.Title>

            <Dialog.Close asChild>
              <Button variant="quiet" aria-label="Close" className="p-1">
                <X size={22} />
              </Button>
            </Dialog.Close>
          </div>

          <TextInput
            aria-label="Find a tag"
            placeholder="Find a tag…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />

          <div className="flex flex-wrap gap-2.5 overflow-y-auto">
            {shown.length === 0 && <p className="text-muted">No tag matches.</p>}

            {shown.map(({ tag, count }) => (
              <button
                key={tag}
                type="button"
                aria-pressed={selected.includes(tag)}
                onClick={() => onToggle(tag)}
                className={cx(
                  'cursor-pointer rounded-full border px-4 py-1.5 text-sm transition',
                  selected.includes(tag)
                    ? 'border-primary bg-primary font-semibold text-primary-foreground'
                    : 'border-border bg-card text-soft hover:border-muted',
                )}
              >
                {tag} <span className="opacity-70">{formatCount(count)}</span>
              </button>
            ))}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
