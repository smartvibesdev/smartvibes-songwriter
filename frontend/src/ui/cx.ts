/** Joins class names, skipping any that are false, null or undefined. */
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}
