import { useState } from 'react'
import { describeError } from './errors'
import { removeById, replaceById } from './lists'
import { useLoaded } from './useLoaded'

/** The four API calls for one kind of item. Declare it outside the component so it stays stable. */
type CrudApi<Item, Input> = {
  list: () => Promise<Item[]>
  create: (input: Input) => Promise<Item>
  update: (id: string, input: Input) => Promise<Item>
  remove: (id: string) => Promise<void>
}

/**
 * The list screen logic shared by Songs and Fragments: load the list, add, edit and
 * delete (with an "are you sure?" step), and track which item is being edited or deleted.
 */
export function useCrudList<Item extends { id: string }, Input>(api: CrudApi<Item, Input>) {
  const { data: items, setData: setItems, error: loadError } = useLoaded(api.list)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [actionError, setActionError] = useState('')

  async function create(input: Input) {
    const created = await api.create(input)

    setItems((current) => [created, ...(current ?? [])])
  }

  async function update(id: string, input: Input) {
    const updated = await api.update(id, input)

    setItems((current) => replaceById(current ?? [], updated))
    setEditingId(null)
  }

  async function confirmDelete() {
    if (deletingId === null) {
      return
    }

    setDeleting(true)
    setActionError('')

    try {
      await api.remove(deletingId)
      setItems((current) => removeById(current ?? [], deletingId))
    } catch (err) {
      setActionError(describeError(err))
    } finally {
      setDeleting(false)
      setDeletingId(null)
    }
  }

  return {
    items,
    loadError,
    actionError,
    editingId,
    setEditingId,
    deletingId,
    setDeletingId,
    deleting,
    create,
    update,
    confirmDelete,
  }
}
