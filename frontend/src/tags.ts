/** "love, rain" becomes ['love', 'rain']. The server also cleans tags up. */
export function parseTags(tagsText: string): string[] {
  return tagsText
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)
}

/** ['love', 'rain'] becomes "love, rain", for editing in a text box. */
export function formatTags(tags: string[]): string {
  return tags.join(', ')
}

/** ['love', 'rain'] becomes "#love #rain", for showing. */
export function hashTags(tags: string[]): string {
  return tags.map((tag) => `#${tag}`).join(' ')
}
