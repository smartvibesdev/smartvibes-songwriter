import { BookOpenText, ChevronDown } from 'lucide-react'
import { type KeyboardEvent, useState } from 'react'
import { type RhymeWord, type WordInfo, lookUpWord } from '../api'
import { describeError } from '../errors'
import { Button } from '../ui/Button'
import { ErrorText } from '../ui/ErrorText'
import { FieldLabel } from '../ui/FieldLabel'
import { TextInput } from '../ui/fields'
import { Spinner } from '../ui/Spinner'

type WordsPanelProps = {
  /** The text selected in the lyrics, to look up with one click. */
  getSelection: () => string
}

/** The first word of some text, or the empty string. */
function firstWord(text: string): string {
  const match = text.match(/[A-Za-z]+(?:['’-][A-Za-z]+)*/)

  return match === null ? '' : match[0]
}

/** Rhymes grouped by syllable count: "1 syllable", "2 syllables", ... */
function groupBySyllables(items: RhymeWord[]): { syllables: number; words: string[] }[] {
  const groups = new Map<number, string[]>()

  for (const { word, syllables } of items) {
    groups.set(syllables, [...(groups.get(syllables) ?? []), word])
  }

  return [...groups.entries()]
    .sort(([first], [second]) => first - second)
    .map(([syllables, words]) => ({ syllables, words }))
}

/** Rhymes, near rhymes, synonyms and antonyms for a word, from dictionaries. No AI, so it costs no tokens. */
export function WordsPanel({ getSelection }: WordsPanelProps) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [info, setInfo] = useState<WordInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function look(word: string) {
    const wanted = word.trim()

    if (wanted.length === 0) {
      return
    }

    setText(wanted)
    setLoading(true)
    setError('')

    try {
      setInfo(await lookUpWord(wanted))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function lookUpSelection() {
    const word = firstWord(getSelection())

    if (word.length === 0) {
      setError('Select a word in the lyrics first.')

      return
    }

    look(word)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') {
      // The panel sits inside the song form, so Enter must not save the song.
      event.preventDefault()
      look(text)
    }
  }

  return (
    <section aria-label="Word tools" className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-4">
      <div className="hidden items-center gap-2 text-sm font-semibold lg:flex">
        <BookOpenText size={16} aria-hidden="true" className="text-accent-text" />
        Rhymes and synonyms
      </div>

      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex cursor-pointer items-center justify-between text-sm font-semibold lg:hidden"
      >
        <span className="flex items-center gap-2">
          <BookOpenText size={16} aria-hidden="true" className="text-accent-text" />
          Rhymes and synonyms
        </span>

        <ChevronDown size={18} aria-hidden="true" className={open ? 'rotate-180' : ''} />
      </button>

      <div className={`${open ? 'flex' : 'hidden'} flex-col gap-4 lg:flex`}>
        <div className="flex gap-2">
          <TextInput
            aria-label="Word to look up"
            placeholder="A word"
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={handleKeyDown}
            maxLength={40}
            className="min-w-0 flex-1 py-2 text-sm"
          />

          <Button variant="outline" className="px-4 py-2" onClick={() => look(text)} disabled={loading}>
            Look up
          </Button>
        </div>

        <Button variant="link" className="self-start text-sm" onClick={lookUpSelection}>
          Use selected word
        </Button>

        {loading && <Spinner small label="Looking up" />}

        {error && <ErrorText>{error}</ErrorText>}

        {info && <WordResults info={info} onPick={look} />}
      </div>
    </section>
  )
}

type WordResultsProps = {
  info: WordInfo
  onPick: (word: string) => void
}

function WordResults({ info, onPick }: WordResultsProps) {
  const syllables = info.syllables.join(' or ')
  const hasNothing =
    info.rhymes.length === 0 &&
    info.near_rhymes.length === 0 &&
    info.synonyms.length === 0 &&
    info.antonyms.length === 0

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted">
        <span className="font-semibold text-foreground">{info.word}</span>
        {syllables && ` · ${syllables} ${syllables === '1' ? 'syllable' : 'syllables'}`}
      </p>

      {hasNothing && <p className="text-sm text-muted">No rhymes or related words found for this word.</p>}

      {info.rhymes_known === false && info.synonyms.length + info.antonyms.length > 0 && (
        <p className="text-sm text-muted">No rhymes: the pronouncing dictionary does not know this word.</p>
      )}

      <RhymeGroup title="Rhymes" items={info.rhymes} onPick={onPick} />

      <RhymeGroup title="Near rhymes" items={info.near_rhymes} onPick={onPick} />

      <WordGroup title="Synonyms" groups={info.synonyms} onPick={onPick} />

      <WordGroup title="Antonyms" groups={info.antonyms} onPick={onPick} />
    </div>
  )
}

function WordChips({ words, onPick }: { words: string[]; onPick: (word: string) => void }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {words.map((word) => (
        <button
          key={word}
          type="button"
          onClick={() => onPick(word)}
          className="cursor-pointer rounded-full border border-border px-2.5 py-0.5 text-sm text-soft hover:border-muted"
        >
          {word}
        </button>
      ))}
    </div>
  )
}

function RhymeGroup({ title, items, onPick }: { title: string; items: RhymeWord[]; onPick: (word: string) => void }) {
  if (items.length === 0) {
    return null
  }

  return (
    <div className="flex flex-col gap-2">
      <FieldLabel>{title}</FieldLabel>

      {groupBySyllables(items).map(({ syllables, words }) => (
        <div key={syllables} className="flex flex-col gap-1">
          <span className="text-xs text-muted">{syllables === 1 ? '1 syllable' : `${syllables} syllables`}</span>

          <WordChips words={words} onPick={onPick} />
        </div>
      ))}
    </div>
  )
}

function WordGroup({
  title,
  groups,
  onPick,
}: {
  title: string
  groups: { part: string; words: string[] }[]
  onPick: (word: string) => void
}) {
  if (groups.length === 0) {
    return null
  }

  return (
    <div className="flex flex-col gap-2">
      <FieldLabel>{title}</FieldLabel>

      {groups.map(({ part, words }) => (
        <div key={part} className="flex flex-col gap-1">
          <span className="text-xs text-muted">{part}</span>

          <WordChips words={words} onPick={onPick} />
        </div>
      ))}
    </div>
  )
}
