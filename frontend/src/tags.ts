/** ['love', 'rain'] becomes "#love #rain", for showing. */
export function hashTags(tags: string[]): string {
  return tags.map((tag) => `#${tag}`).join(' ')
}

/** The most tags one song or fragment can have, and the longest a tag can be. Same limits as the server. */
export const TAG_LIMITS = { count: 10, length: 30 }

/** "  #Love " becomes "love". Returns '' when nothing is left. */
export function cleanTag(text: string): string {
  return text.trim().replace(/^#+/, '').trim().toLowerCase().slice(0, TAG_LIMITS.length)
}

/** True when both lists hold the same tags in the same order. */
export function sameTags(first: string[], second: string[]): boolean {
  return first.length === second.length && first.every((tag, index) => tag === second[index])
}
