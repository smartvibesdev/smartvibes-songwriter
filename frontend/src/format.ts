/** An ISO timestamp from the API as a short local date, e.g. "Oct 1, 2026". */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

/** A number with thousands separators, e.g. 5284 becomes "5,284". */
export function formatCount(count: number): string {
  return count.toLocaleString()
}
