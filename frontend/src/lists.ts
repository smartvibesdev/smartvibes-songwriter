/** A copy of `items` with the item that has this id swapped for `updated`. */
export function replaceById<T extends { id: string }>(items: T[], updated: T): T[] {
  return items.map((item) => (item.id === updated.id ? updated : item))
}

/** A copy of `items` without the item that has this id. */
export function removeById<T extends { id: string }>(items: T[], id: string): T[] {
  return items.filter((item) => item.id !== id)
}

/** A copy of `items` with `item` added, or removed if it was already there. */
export function toggleItem<T>(items: T[], item: T): T[] {
  if (items.includes(item)) {
    return items.filter((existing) => existing !== item)
  }

  return [...items, item]
}
