import { useState } from 'react'
import { describeError } from '../errors'

/** The API calls that change one kind of item. Declare it outside the component so it stays stable. */
type ItemApi<Item, Input> = {
  create: (input: Input) => Promise<Item>
  update: (id: string, input: Input) => Promise<Item>
  remove: (id: string) => Promise<void>
}

/**
 * Adding, editing and deleting one kind of item (songs or fragments), with an "are you sure?"
 * step before a delete, and which item is being edited or deleted. `onChange` is called after
 * every change so the lists that show these items can load again.
 */
export function useItemActions<Item, Input>(api: ItemApi<Item, Input>, onChange: () => void) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [actionError, setActionError] = useState('')

  async function create(input: Input) {
    await api.create(input)
    onChange()
  }

  async function update(id: string, input: Input) {
    await api.update(id, input)
    setEditingId(null)
    onChange()
  }

  async function confirmDelete() {
    if (deletingId === null) {
      return
    }

    setDeleting(true)
    setActionError('')

    try {
      await api.remove(deletingId)
      onChange()
    } catch (err) {
      setActionError(describeError(err))
    } finally {
      setDeleting(false)
      setDeletingId(null)
    }
  }

  return { actionError, editingId, setEditingId, deletingId, setDeletingId, deleting, create, update, confirmDelete }
}

/** What the hook returns, for passing to the screen's parts. */
export type ItemActions<Item, Input> = ReturnType<typeof useItemActions<Item, Input>>
