import * as Dialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from './Button'

type FormDialogProps = {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
}

/** A box over the page that holds a form, so adding something does not push the list down. */
export function FormDialog({ open, title, onClose, children }: FormDialogProps) {
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
          className="fixed top-1/2 left-1/2 z-50 flex max-h-[90vh] w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 -translate-y-1/2 flex-col gap-5 overflow-y-auto rounded-3xl border border-border bg-card p-6 shadow-2xl sm:p-8"
        >
          <div className="flex items-center justify-between">
            <Dialog.Title className="font-display text-2xl font-semibold">{title}</Dialog.Title>

            <Dialog.Close asChild>
              <Button variant="quiet" aria-label="Close" className="p-1">
                <X size={22} />
              </Button>
            </Dialog.Close>
          </div>

          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
