import { type ReactNode, useCallback, useEffect, useRef, useState } from 'react'
import {
  type ChatContext,
  type ChatMessageInput,
  chatWithAssistant,
  getAiUsage,
  lookUpWord,
  type TokenBudget,
} from '../api'
import { describeError } from '../errors'
import { useAppState } from '../state/AppStateContext'
import {
  AssistantContext,
  type AssistantMessage,
  type DictionaryFocus,
  HOME_PROMPTS,
  type PageTools,
  type QuickPrompt,
  SONG_PROMPTS,
} from './AssistantContext'
import { parseDictionaryRequest, toLookup } from './dictionaryRequest'

const DEFAULT_DIAL = 5

const FOCUS_NAMES: Record<DictionaryFocus, string> = {
  rhymes: 'rhymes',
  synonyms: 'other words',
  antonyms: 'opposites',
}

/** The conversation as the assistant should see it: what was said, plus a note of any change it made. */
function toHistory(messages: AssistantMessage[]): ChatMessageInput[] {
  const history: ChatMessageInput[] = []

  for (const message of messages) {
    if (message.role === 'user') {
      history.push({ role: 'user', content: message.sentText ?? message.text })
    }

    if (message.role === 'assistant') {
      const note = message.edit ? ` [${message.edit.summary}]` : ''

      history.push({ role: 'assistant', content: message.text + note })
    }
  }

  return history
}

function contextFor(tools: PageTools | null): ChatContext {
  if (tools === null) {
    return { page: 'home', title: '', lyrics: '', selection: '', selection_start_line: null, selection_end_line: null }
  }

  const page = tools.getContext()

  return {
    page: 'song',
    title: page.title,
    lyrics: page.lyrics,
    selection: page.selection,
    selection_start_line: page.selectionStartLine,
    selection_end_line: page.selectionEndLine,
  }
}

/**
 * Holds the assistant's conversation above the pages, so it stays when you move between them and
 * the drawer stays open or closed as you left it. Signing out removes it, so nothing carries over.
 */
export function AssistantProvider({ children }: { children: ReactNode }) {
  const { fragments } = useAppState()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<AssistantMessage[]>([])
  const [running, setRunning] = useState(false)
  const [budget, setBudget] = useState<TokenBudget | null>(null)
  const [dial, setDial] = useState(DEFAULT_DIAL)
  const [hasSongTools, setHasSongTools] = useState(false)
  const pageTools = useRef<PageTools | null>(null)
  const nextId = useRef(1)

  // The budget is asked for the first time the assistant opens, not on every page load.
  useEffect(() => {
    if (open && budget === null) {
      getAiUsage()
        .then(setBudget)
        .catch(() => undefined)
    }
  }, [open, budget])

  function addMessage(message: Omit<AssistantMessage, 'id'>) {
    const id = nextId.current

    nextId.current += 1
    setMessages((current) => [...current, { ...message, id }])
  }

  function changeMessage(messageId: number, changes: Partial<AssistantMessage>) {
    setMessages((current) =>
      current.map((message) => (message.id === messageId ? { ...message, ...changes } : message)),
    )
  }

  async function answerFromDictionary(word: string, focus: DictionaryFocus) {
    setRunning(true)

    try {
      const info = await lookUpWord(word)

      addMessage({
        role: 'assistant',
        text: `Here are ${FOCUS_NAMES[focus]} for "${info.word}" from the dictionary.`,
        dictionary: { lookups: [toLookup(info)], free: true, focus },
      })
    } catch (err) {
      addMessage({ role: 'error', text: describeError(err) })
    } finally {
      setRunning(false)
    }
  }

  async function askAssistant(history: ChatMessageInput[], saveable: boolean) {
    const tools = pageTools.current

    setRunning(true)

    try {
      const reply = await chatWithAssistant({ messages: history, context: contextFor(tools), dial })
      const result = applyReply(reply, tools)

      addMessage({
        role: 'assistant',
        text: result.text,
        tokens: reply.tokens.input + reply.tokens.output,
        saveable,
        edit: result.edit,
        dictionary: reply.dictionary.length > 0 ? { lookups: reply.dictionary, free: false, focus: null } : undefined,
      })
      setBudget(reply.budget)
    } catch (err) {
      addMessage({ role: 'error', text: describeError(err) })
    } finally {
      setRunning(false)
    }
  }

  /** Puts the assistant's changes into the song page, if it is still open. */
  function applyReply(reply: Awaited<ReturnType<typeof chatWithAssistant>>, tools: PageTools | null) {
    const hasChanges = reply.edits.length > 0 || reply.title !== null

    if (hasChanges === false) {
      return { text: reply.text, edit: undefined }
    }

    if (tools === null) {
      return { text: `${reply.text}\n\n(The song page is closed, so these changes were not made.)`, edit: undefined }
    }

    const previousTitle = reply.title === null ? null : tools.getContext().title
    const summaries: string[] = []
    let changedLyrics = false

    if (reply.edits.length > 0) {
      const summary = tools.applyEdits(reply.edits)

      if (summary === null) {
        return {
          text: `${reply.text}\n\n(Those changes did not fit the lyrics, so nothing was changed.)`,
          edit: undefined,
        }
      }

      summaries.push(summary)
      changedLyrics = true
    }

    if (reply.title !== null) {
      tools.setTitle(reply.title)
      summaries.push('Changed the title')
    }

    return {
      text: reply.text,
      edit: { summary: summaries.join(' · '), changedLyrics, previousTitle, undone: false },
    }
  }

  async function send(text: string, display?: string, saveable = false) {
    const trimmed = text.trim()

    if (trimmed.length === 0 || running) {
      return
    }

    const history = toHistory(messages)

    addMessage({ role: 'user', text: display ?? trimmed, sentText: trimmed })

    const dictionaryRequest = parseDictionaryRequest(trimmed)

    if (dictionaryRequest !== null) {
      await answerFromDictionary(dictionaryRequest.word, dictionaryRequest.focus)

      return
    }

    await askAssistant([...history, { role: 'user', content: trimmed }], saveable)
  }

  async function runPrompt(prompt: QuickPrompt) {
    const selection = pageTools.current?.getContext().selection ?? ''

    if (prompt.needsSelection && selection === '') {
      addMessage({ role: 'user', text: prompt.label })
      addMessage({ role: 'assistant', text: 'Select the lines you want improved in the lyrics first, then try again.' })

      return
    }

    await send(prompt.text, prompt.label, prompt.saveable === true)
  }

  function undoEdit(messageId: number) {
    const message = messages.find((item) => item.id === messageId)

    if (message?.edit === undefined || message.edit.undone) {
      return
    }

    if (message.edit.changedLyrics) {
      pageTools.current?.undoEdits()
    }

    if (message.edit.previousTitle !== null) {
      pageTools.current?.setTitle(message.edit.previousTitle)
    }

    changeMessage(messageId, { edit: { ...message.edit, undone: true } })
  }

  async function saveAsFragment(messageId: number) {
    const text = messages.find((item) => item.id === messageId)?.text ?? ''

    try {
      await fragments.create({ text, tags: ['ai'] })
      changeMessage(messageId, { outcome: 'Saved as a fragment, tagged "ai"' })
    } catch (err) {
      addMessage({ role: 'error', text: describeError(err) })
    }
  }

  const registerPageTools = useCallback((tools: PageTools | null) => {
    pageTools.current = tools
    setHasSongTools(tools !== null)
  }, [])

  return (
    <AssistantContext.Provider
      value={{
        open,
        setOpen,
        messages,
        running,
        budget,
        dial,
        setDial,
        hasSongTools,
        prompts: hasSongTools ? SONG_PROMPTS : HOME_PROMPTS,
        send: (text) => send(text),
        runPrompt,
        clear: () => setMessages([]),
        registerPageTools,
        undoEdit,
        saveAsFragment,
      }}
    >
      {children}
    </AssistantContext.Provider>
  )
}
