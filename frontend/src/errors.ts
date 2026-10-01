/** Turns anything that was thrown into a message fit to show the user. */
export function describeError(err: unknown): string {
  if (err instanceof Error) {
    return err.message
  }

  return String(err)
}
