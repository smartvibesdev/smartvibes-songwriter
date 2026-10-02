import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { ChevronDown } from 'lucide-react'
import { Button } from './Button'

const ITEM =
  'cursor-pointer rounded-xl px-4 py-2.5 text-[15px] text-foreground outline-none ' +
  'data-[highlighted]:bg-primary/10 data-[highlighted]:text-primary-text'

type NewMenuProps = {
  onNewFragment: () => void
  onNewSong: () => void
}

/** One blue "New" button that opens a small menu to add a fragment or a song. */
export function NewMenu({ onNewFragment, onNewSong }: NewMenuProps) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <Button>
          New
          <ChevronDown size={16} aria-hidden="true" />
        </Button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className="z-50 min-w-44 rounded-2xl border border-border bg-card p-2 shadow-xl"
        >
          <DropdownMenu.Item className={ITEM} onSelect={onNewFragment}>
            Fragment
          </DropdownMenu.Item>

          <DropdownMenu.Item className={ITEM} onSelect={onNewSong}>
            Song
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
