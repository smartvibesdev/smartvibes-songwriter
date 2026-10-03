import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { LogOut, Menu } from 'lucide-react'
import { Button } from './Button'

type AccountMenuProps = {
  onSignOut: () => void
  signingOut: boolean
}

/** The menu button for narrow screens (a hamburger). It holds the account actions. */
export function AccountMenu({ onSignOut, signingOut }: AccountMenuProps) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <Button variant="quiet" aria-label="Open menu" title="Menu" className="p-2">
          <Menu size={22} aria-hidden="true" />
        </Button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className="z-50 min-w-48 rounded-2xl border border-border bg-card p-2 shadow-xl"
        >
          <DropdownMenu.Item
            disabled={signingOut}
            onSelect={onSignOut}
            className={
              'flex cursor-pointer items-center gap-3 rounded-xl px-4 py-3 text-[15px] text-foreground outline-none ' +
              'data-[disabled]:opacity-50 data-[highlighted]:bg-primary/10 data-[highlighted]:text-primary-text'
            }
          >
            <LogOut size={18} aria-hidden="true" />
            Sign out
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
