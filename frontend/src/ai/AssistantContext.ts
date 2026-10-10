import { createContext, useContext } from 'react'
import type { ChatEdit, DictionaryLookup, TokenBudget } from '../api'

/** What the song page shows right now. Line numbers start at 1. */
export type PageContext = {
  title: string
  lyrics: string
  selection: string
  selectionStartLine: number | null
  selectionEndLine: number | null
}

/** What the song page lets the assistant do. */
export type PageTools = {
  getContext: () => PageContext
  setTitle: (text: string) => void
  /** Returns a description such as "Changed lines 4–7", or null if the changes did not fit. */
  applyEdits: (edits: ChatEdit[]) => string | null
  /** Take back the last change to the lyrics. */
  undoEdits: () => void
}

/** Which dictionary answer to show: rhymes (with near rhymes), synonyms or antonyms. */
export type DictionaryFocus = 'rhymes' | 'synonyms' | 'antonyms'

/** A suggested job the user can start with one click. */
export type QuickPrompt = {
  id: string
  /** The words on the button, and in the chat. */
  label: string
  /** What is sent. When `fill` is true it is put in the message box for the user to finish. */
  text: string
  fill?: boolean
  /** The prompt makes no sense without lines selected in the lyrics. */
  needsSelection?: boolean
  /** The answer is a line the user may want to save as a fragment. */
  saveable?: boolean
}

const WORD_PROMPTS: QuickPrompt[] = [
  { id: 'rhymes', label: 'Rhymes for…', text: 'What rhymes with ', fill: true },
  { id: 'synonyms', label: 'Another word for…', text: 'Another word for ', fill: true },
  { id: 'antonyms', label: 'Opposite of…', text: 'Opposite of ', fill: true },
]

const SECTION_NOTE = 'that fits this song and add it to the lyrics'

export const SONG_PROMPTS: QuickPrompt[] = [
  { id: 'verse', label: 'Write a verse', text: `Write a new verse ${SECTION_NOTE}.` },
  { id: 'chorus', label: 'Write a chorus', text: `Write a chorus ${SECTION_NOTE}.` },
  { id: 'improve', label: 'Improve selection', text: 'Improve the selected lines.', needsSelection: true },
  {
    id: 'review',
    label: 'Review song',
    text: 'Review this song: tense, point of view, clichés and imagery. Do not change anything.',
  },
  { id: 'intro', label: 'Write an intro', text: `Write an intro ${SECTION_NOTE}, at the top.` },
  { id: 'bridge', label: 'Write a bridge', text: `Write a bridge ${SECTION_NOTE}.` },
  { id: 'outro', label: 'Write an outro', text: `Write an outro ${SECTION_NOTE}.` },
  {
    id: 'titles',
    label: 'Suggest titles',
    text: 'Suggest five titles for this song. Do not change the title.',
  },
  ...WORD_PROMPTS,
]

export const HOME_PROMPTS: QuickPrompt[] = [
  {
    id: 'fragment',
    label: 'Give me a fresh line',
    text: 'Write one short lyric fragment of one or two lines, the kind a songwriter jots down to use later.',
    saveable: true,
  },
  ...WORD_PROMPTS,
]

/** One line of the conversation. */
export type AssistantMessage = {
  id: number
  role: 'user' | 'assistant' | 'error'
  text: string
  /** What is sent to the assistant for a user message, when it differs from `text` (quick prompts). */
  sentText?: string
  /** Tokens the answer cost (assistant messages only). */
  tokens?: number
  /** The answer is a line the user may save as a fragment. */
  saveable?: boolean
  /** What the user did with this answer ("Saved as a fragment"), shown in place of its button. */
  outcome?: string
  /** A change the assistant made to the song, which can be undone. */
  edit?: { summary: string; changedLyrics: boolean; previousTitle: string | null; undone: boolean }
  /** Dictionary answers. `free` is true when they came from the dictionaries alone, with no AI. */
  dictionary?: { lookups: DictionaryLookup[]; free: boolean; focus: DictionaryFocus | null }
}

export type AssistantState = {
  open: boolean
  setOpen: (open: boolean) => void
  messages: AssistantMessage[]
  running: boolean
  /** Today's token budget, or null until it has loaded (it loads when the assistant first opens). */
  budget: TokenBudget | null
  dial: number
  setDial: (dial: number) => void
  /** True while the song page is on screen, so the assistant can change the song. */
  hasSongTools: boolean
  /** The prompts that suit the page on screen. */
  prompts: QuickPrompt[]
  /** Send something the user typed. Rhyme, synonym and antonym questions are answered without AI. */
  send: (text: string) => Promise<void>
  /** Run a quick prompt. */
  runPrompt: (prompt: QuickPrompt) => Promise<void>
  /** Forget the conversation. */
  clear: () => void
  registerPageTools: (tools: PageTools | null) => void
  undoEdit: (messageId: number) => void
  saveAsFragment: (messageId: number) => Promise<void>
}

export const AssistantContext = createContext<AssistantState | null>(null)

/** The AI assistant's state. Only works inside `AssistantProvider`. */
export function useAssistant(): AssistantState {
  const state = useContext(AssistantContext)

  if (state === null) {
    throw new Error('useAssistant must be used inside AssistantProvider')
  }

  return state
}
