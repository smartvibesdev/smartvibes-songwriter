import { ArrowUp, Eraser, SlidersHorizontal, Sparkles, X } from 'lucide-react'
import { type FormEvent, useEffect, useRef, useState } from 'react'
import { formatCount } from '../format'
import { Button } from '../ui/Button'
import { cx } from '../ui/cx'
import { ErrorText } from '../ui/ErrorText'
import { FieldLabel } from '../ui/FieldLabel'
import { TextInput } from '../ui/fields'
import { Spinner } from '../ui/Spinner'
import { type AssistantMessage, type DictionaryFocus, useAssistant } from './AssistantContext'

const TOP_OF_DIAL_HINTS: Record<number, string> = {
  8: 'Adds two random words to work in.',
  9: 'Adds random words and an unusual point of view.',
  10: 'Adds random words, a point of view and a strange rule.',
}

function dialHint(dial: number): string {
  if (dial === 0) {
    return 'Plain, literal and predictable.'
  }

  if (dial >= 8) {
    return TOP_OF_DIAL_HINTS[dial]
  }

  return 'Gets more surprising as it goes up.'
}

// Phones: a sheet from the bottom, half the screen (or nearly all of it when enlarged).
// Wide screens: a column down the right edge, half the screen wide.
// Only the first few prompts show until "More" is pressed, so the conversation keeps its room.
const FEATURED_PROMPTS = 4

const SHEET_CLASSES =
  'fixed inset-x-0 bottom-0 z-30 flex flex-col border border-border bg-sheet shadow-2xl rounded-t-3xl ' +
  'lg:inset-y-0 lg:left-auto lg:h-dvh lg:w-1/2 lg:rounded-none lg:border-y-0 lg:border-r-0'

/** The AI assistant: a round button on every page that opens a drawer (wide screens) or sheet (phones). */
export function Assistant() {
  const { open, setOpen } = useAssistant()

  if (open === false) {
    return (
      <button
        type="button"
        aria-label="Open the AI assistant"
        onClick={() => setOpen(true)}
        className="fixed right-4 bottom-4 z-30 flex size-12 cursor-pointer items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-text"
      >
        <Sparkles size={22} aria-hidden="true" />
      </button>
    )
  }

  return <AssistantSheet />
}

function AssistantSheet() {
  const { setOpen, messages, running, budget, dial, prompts, send, runPrompt, clear, hasSongTools } = useAssistant()
  const [text, setText] = useState('')
  const [enlarged, setEnlarged] = useState(false)
  const [showOptions, setShowOptions] = useState(false)
  const [showAllPrompts, setShowAllPrompts] = useState(false)
  const endOfMessages = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const shownPrompts = showAllPrompts ? prompts : prompts.slice(0, FEATURED_PROMPTS)
  const placeholder = hasSongTools ? 'Ask anything about this song' : 'Ask anything'

  // Show the newest message.
  useEffect(() => {
    endOfMessages.current?.scrollIntoView({ block: 'end' })
  }, [messages.length, running])

  function handleSubmit(event: FormEvent) {
    event.preventDefault()

    if (text.trim().length > 0 && running === false) {
      send(text)
      setText('')
    }
  }

  function handlePrompt(index: number) {
    const prompt = prompts[index]

    if (prompt.fill) {
      // The user finishes the sentence ("What rhymes with …") and sends it.
      setText(prompt.text)
      input.current?.focus()
    } else {
      runPrompt(prompt)
    }
  }

  return (
    <aside aria-label="AI assistant" className={cx(SHEET_CLASSES, enlarged ? 'h-[92dvh]' : 'h-[50dvh]')}>
      {/* Phones: the bar at the top makes the sheet taller or shorter. */}
      <button
        type="button"
        aria-label={enlarged ? 'Make the assistant smaller' : 'Make the assistant larger'}
        onClick={() => setEnlarged(!enlarged)}
        className="flex cursor-pointer justify-center pt-2 pb-1 lg:hidden"
      >
        <span className="h-1 w-10 rounded-full bg-border" />
      </button>

      <div className="flex items-center justify-between px-4 pt-1 pb-2 lg:pt-3">
        <h2 className="flex items-center gap-2 font-display text-lg font-semibold">
          <Sparkles size={18} aria-hidden="true" className="text-accent-text" />
          Assistant
        </h2>

        <div className="flex items-center gap-1">
          {budget && <p className="mr-1 text-xs text-muted">{formatCount(budget.remaining)} tokens left</p>}

          <Button
            variant="quiet"
            className="p-1"
            aria-label={`Wildness ${dial} of 10`}
            aria-expanded={showOptions}
            title={`Wildness ${dial} / 10`}
            onClick={() => setShowOptions(!showOptions)}
          >
            <SlidersHorizontal size={18} />
          </Button>

          {messages.length > 0 && (
            <Button
              variant="quiet"
              className="p-1"
              aria-label="Clear the conversation"
              title="Clear the conversation"
              onClick={clear}
            >
              <Eraser size={18} />
            </Button>
          )}

          <Button variant="quiet" className="p-1" aria-label="Close the assistant" onClick={() => setOpen(false)}>
            <X size={22} />
          </Button>
        </div>
      </div>

      {showOptions && (
        <div className="px-4 pb-2">
          <WildnessDial />
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-2" aria-live="polite">
        {messages.length === 0 && (
          <p className="text-sm text-muted">
            {hasSongTools
              ? 'Ask for a verse, a rewrite, a review, or a rhyme. I can change the lyrics for you, and you can undo it.'
              : 'Ask for a fresh line, or a rhyme, synonym or antonym.'}
          </p>
        )}

        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}

        {running && <Spinner small label="Working" />}

        <div ref={endOfMessages} />
      </div>

      <div className="flex flex-col gap-3 border-t border-border px-4 pt-3 pb-4">
        <div className="flex gap-2 overflow-x-auto [scrollbar-width:none] lg:flex-wrap lg:overflow-visible">
          {shownPrompts.map((prompt, index) => (
            <button
              key={prompt.id}
              type="button"
              disabled={running}
              onClick={() => handlePrompt(index)}
              className="shrink-0 cursor-pointer rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold whitespace-nowrap text-primary-text hover:border-muted disabled:cursor-not-allowed disabled:opacity-50"
            >
              {prompt.label}
            </button>
          ))}

          {prompts.length > FEATURED_PROMPTS && (
            <button
              type="button"
              aria-expanded={showAllPrompts}
              onClick={() => setShowAllPrompts(!showAllPrompts)}
              className="shrink-0 cursor-pointer rounded-full px-3 py-1 text-xs font-semibold whitespace-nowrap text-muted hover:text-foreground"
            >
              {showAllPrompts ? 'Fewer' : 'More…'}
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <TextInput
            ref={input}
            aria-label="Message the assistant"
            placeholder={placeholder}
            value={text}
            onChange={(event) => setText(event.target.value)}
            maxLength={2000}
            className="min-w-0 flex-1 rounded-full py-2 text-sm"
          />

          <button
            type="submit"
            aria-label="Send"
            disabled={running || text.trim().length === 0}
            className="flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-full bg-primary text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <ArrowUp size={18} aria-hidden="true" />
          </button>
        </form>
      </div>
    </aside>
  )
}

function Message({ message }: { message: AssistantMessage }) {
  if (message.role === 'user') {
    return (
      <p className="max-w-[92%] self-end rounded-2xl rounded-br-md bg-primary px-3 py-2 text-sm text-primary-foreground">
        {message.text}
      </p>
    )
  }

  if (message.role === 'error') {
    return <ErrorText>{message.text}</ErrorText>
  }

  return (
    <div className="flex max-w-[96%] flex-col gap-2 self-start rounded-2xl rounded-bl-md border border-border bg-card px-3 py-2">
      <p className="text-sm leading-snug whitespace-pre-line">{message.text}</p>

      {message.dictionary && (
        <DictionaryAnswer
          lookups={message.dictionary.lookups}
          free={message.dictionary.free}
          focus={message.dictionary.focus}
        />
      )}

      {message.edit && <EditNotice message={message} />}

      {message.tokens !== undefined && <p className="text-xs text-muted">{formatCount(message.tokens)} tokens used</p>}

      <SaveButton message={message} />
    </div>
  )
}

function EditNotice({ message }: { message: AssistantMessage }) {
  const { hasSongTools, undoEdit } = useAssistant()
  const edit = message.edit

  if (edit === undefined) {
    return null
  }

  return (
    <div className="flex items-center justify-between gap-3 rounded-lg bg-accent/15 px-2.5 py-1.5 text-sm">
      <span>{edit.undone ? `${edit.summary} (undone)` : edit.summary}</span>

      {edit.undone === false && hasSongTools && (
        <button
          type="button"
          onClick={() => undoEdit(message.id)}
          className="cursor-pointer rounded-full border border-border bg-card px-2.5 py-0.5 text-xs font-semibold hover:border-muted"
        >
          Undo
        </button>
      )}
    </div>
  )
}

function SaveButton({ message }: { message: AssistantMessage }) {
  const { saveAsFragment } = useAssistant()

  if (message.outcome) {
    return <p className="text-sm font-semibold text-accent-text">{message.outcome}</p>
  }

  if (message.saveable) {
    return (
      <Button variant="link" className="self-start text-sm" onClick={() => saveAsFragment(message.id)}>
        Save as fragment
      </Button>
    )
  }

  return null
}

const CHIP_QUESTIONS: Record<DictionaryFocus, string> = {
  rhymes: 'What rhymes with ',
  synonyms: 'Another word for ',
  antonyms: 'Opposite of ',
}

type DictionaryAnswerProps = {
  lookups: {
    word: string
    rhymes: string[]
    near_rhymes: string[]
    slant_rhymes: string[]
    synonyms: string[]
    antonyms: string[]
  }[]
  free: boolean
  focus: DictionaryFocus | null
}

/** Rhymes, synonyms or antonyms as word chips. Clicking one asks the same question about that word. */
function DictionaryAnswer({ lookups, free, focus }: DictionaryAnswerProps) {
  const { send } = useAssistant()
  const question = CHIP_QUESTIONS[focus ?? 'rhymes']

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[10px] font-semibold tracking-[0.08em] text-accent-text uppercase">
        {free ? 'Dictionary · no tokens' : 'Dictionary'}
      </p>

      {lookups.map((lookup) => {
        const groups = [
          { title: 'Rhymes', words: lookup.rhymes, show: focus === null || focus === 'rhymes' },
          { title: 'Near rhymes', words: lookup.near_rhymes, show: focus === null || focus === 'rhymes' },
          {
            title: 'Slant rhymes (same vowel sounds)',
            words: lookup.slant_rhymes,
            show: focus === null || focus === 'rhymes',
          },
          { title: 'Synonyms', words: lookup.synonyms, show: focus === null || focus === 'synonyms' },
          { title: 'Antonyms', words: lookup.antonyms, show: focus === null || focus === 'antonyms' },
        ].filter((group) => group.show && group.words.length > 0)

        return (
          <div key={lookup.word} className="flex flex-col gap-2">
            {lookups.length > 1 && <FieldLabel>{lookup.word}</FieldLabel>}

            {groups.length === 0 && <p className="text-sm text-muted">Nothing found for "{lookup.word}".</p>}

            {groups.map((group) => (
              <div key={group.title} className="flex flex-col gap-1">
                <span className="text-xs text-muted">{group.title}</span>

                <div className="flex flex-wrap gap-1.5">
                  {group.words.map((word) => (
                    <button
                      key={word}
                      type="button"
                      onClick={() => send(`${question}${word}`)}
                      className="cursor-pointer rounded-full border border-border px-2.5 py-0.5 text-sm text-soft hover:border-muted"
                    >
                      {word}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}

function WildnessDial() {
  const { dial, setDial } = useAssistant()

  return (
    <label className="flex flex-col gap-1.5">
      <span className="flex items-center justify-between">
        <FieldLabel>Wildness</FieldLabel>

        <span className="text-sm text-muted">{dial} / 10</span>
      </span>

      <input
        type="range"
        min={0}
        max={10}
        step={1}
        value={dial}
        onChange={(event) => setDial(Number(event.target.value))}
        className="w-full cursor-pointer accent-primary"
      />

      <span className="text-xs text-muted">{dialHint(dial)}</span>
    </label>
  )
}
