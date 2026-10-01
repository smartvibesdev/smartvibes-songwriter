/** An ISO timestamp from the API as a short local date, e.g. "10/1/2026". */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString()
}
