import type { DictionaryLookup, WordInfo } from '../api'
import type { DictionaryFocus } from './AssistantContext'

const WORD = "([a-z]+(?:['’-][a-z]+)*)"

// "What rhymes with stone?", "rhymes for stone", "another word for heavy", "opposite of dark" ...
const PATTERNS: { focus: DictionaryFocus; pattern: RegExp }[] = [
  { focus: 'rhymes', pattern: new RegExp(`^(?:what |which words? )?rhymes?(?: with| for)? ${WORD}\\s*[?.!]*$`, 'i') },
  {
    focus: 'synonyms',
    pattern: new RegExp(
      `^(?:another word|other words?|words?|synonyms?)(?: for| like| meaning| of) ${WORD}\\s*[?.!]*$`,
      'i',
    ),
  },
  { focus: 'antonyms', pattern: new RegExp(`^(?:the )?(?:opposites?|antonyms?)(?: of| for) ${WORD}\\s*[?.!]*$`, 'i') },
]

/** A message that is just a rhyme, synonym or antonym question about one word, or null. Those need no AI. */
export function parseDictionaryRequest(text: string): { word: string; focus: DictionaryFocus } | null {
  const trimmed = text.trim()

  for (const { focus, pattern } of PATTERNS) {
    const match = trimmed.match(pattern)

    if (match !== null) {
      return { word: match[1].toLowerCase(), focus }
    }
  }

  return null
}

/** The shorter, flat form that the chat shows. */
export function toLookup(info: WordInfo): DictionaryLookup {
  const flat = (groups: { words: string[] }[]) => [...new Set(groups.flatMap((group) => group.words))]

  return {
    word: info.word,
    rhymes: info.rhymes.map((item) => item.word).slice(0, 30),
    near_rhymes: info.near_rhymes.map((item) => item.word).slice(0, 20),
    slant_rhymes: info.slant_rhymes.map((item) => item.word).slice(0, 30),
    synonyms: flat(info.synonyms).slice(0, 20),
    antonyms: flat(info.antonyms).slice(0, 20),
  }
}
