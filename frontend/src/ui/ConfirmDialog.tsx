import * as AlertDialog from '@radix-ui/react-alert-dialog'
import { Button } from './Button'

type ConfirmDialogProps = {
  open: boolean
  title: string
  description: string
  confirmLabel: string
  /** True while the action is running, so the button cannot be pressed twice. */
  pending: boolean
  onConfirm: () => void
  onCancel: () => void
}

/** An in-page "are you sure?" box, in place of the browser's confirm pop-up. */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  pending,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  function handleOpenChange(next: boolean) {
    if (next === false) {
      onCancel()
    }
  }

  return (
    <AlertDialog.Root open={open} onOpenChange={handleOpenChange}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 z-40 bg-[#0f1630]/50" />

        <AlertDialog.Content className="fixed top-1/2 left-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-3xl border border-border bg-card p-8 shadow-2xl">
          <AlertDialog.Title className="font-display text-2xl font-semibold">{title}</AlertDialog.Title>

          <AlertDialog.Description className="mt-3 leading-relaxed text-soft">{description}</AlertDialog.Description>

          <div className="mt-8 flex justify-end gap-3">
            <AlertDialog.Cancel asChild>
              <Button variant="outline">Cancel</Button>
            </AlertDialog.Cancel>

            <Button variant="danger" onClick={onConfirm} disabled={pending}>
              {confirmLabel}
            </Button>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  )
}
