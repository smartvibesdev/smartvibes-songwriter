import { ChevronDown, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { type GenerateKind, type Generated, LIMITS, type TokenBudget, generateText, getAiUsage } from '../api'
import { describeError } from '../errors'
import { formatCount } from '../format'
import { useLoaded } from '../useLoaded'
import { Button } from '../ui/Button'
import { ErrorText } from '../ui/ErrorText'
import { FieldLabel } from '../ui/FieldLabel'
import { TextArea } from '../ui/fields'
import { Spinner } from '../ui/Spinner'

const KINDS: { value: GenerateKind; label: string }[] = [
  { value: 'title', label: 'Title' },
  { value: 'lyrics', label: 'Lyrics' },
  { value: 'fragment', label: 'Fragment' },
]

const DEFAULT_DIAL = 5

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

type GeneratePanelProps = {
  /** Put generated text in the title field. */
  onUseTitle: (text: string) => void
  /** Add generated text to the end of the lyrics. */
  onAddToLyrics: (text: string) => void
  /** Save generated text as a new fragment. */
  onSaveFragment: (text: string) => Promise<void>
}

/** The AI writing tools beside the song editor: what to write, a seed, the wildness dial, and the result. */
export function GeneratePanel({ onUseTitle, onAddToLyrics, onSaveFragment }: GeneratePanelProps) {
  const [open, setOpen] = useState(false)
  const [kind, setKind] = useState<GenerateKind>('lyrics')
  const [seed, setSeed] = useState('')
  const [dial, setDial] = useState(DEFAULT_DIAL)
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<Generated | null>(null)
  const [latestBudget, setLatestBudget] = useState<TokenBudget | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const { data: loadedBudget } = useLoaded(getAiUsage)
  const budget = latestBudget ?? loadedBudget

  async function generate() {
    setGenerating(true)
    setError('')
    setNotice('')

    try {
      const generated = await generateText({ kind, seed, dial })

      setResult(generated)
      setLatestBudget(generated.budget)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setGenerating(false)
    }
  }

  function accept(apply: (text: string) => void) {
    if (result === null) {
      return
    }

    apply(result.text)
    setResult(null)
  }

  async function saveAsFragment() {
    if (result === null) {
      return
    }

    setSaving(true)
    setError('')

    try {
      await onSaveFragment(result.text)
      setResult(null)
      setNotice('Saved as a fragment, tagged "ai".')
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section aria-label="AI writing tools" className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-4">
      <div className="hidden items-center gap-2 text-sm font-semibold lg:flex">
        <Sparkles size={16} aria-hidden="true" className="text-accent-text" />
        AI writing tools
      </div>

      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex cursor-pointer items-center justify-between text-sm font-semibold lg:hidden"
      >
        <span className="flex items-center gap-2">
          <Sparkles size={16} aria-hidden="true" className="text-accent-text" />
          AI writing tools
        </span>

        <ChevronDown size={18} aria-hidden="true" className={open ? 'rotate-180' : ''} />
      </button>

      <div className={`${open ? 'flex' : 'hidden'} flex-col gap-4 lg:flex`}>
        <div role="radiogroup" aria-label="What to write" className="grid grid-cols-3 gap-2">
          {KINDS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={kind === value}
              onClick={() => setKind(value)}
              className={`cursor-pointer rounded-xl border px-3 py-2 text-sm font-semibold transition ${
                kind === value
                  ? 'border-primary bg-primary/10 text-primary-text'
                  : 'border-border text-muted hover:text-foreground'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <TextArea
          aria-label="Seed (optional)"
          placeholder="Seed: an idea or some text (optional)"
          value={seed}
          onChange={(event) => setSeed(event.target.value)}
          maxLength={LIMITS.aiSeed}
          rows={3}
          className="text-sm"
        />

        <label className="flex flex-col gap-2">
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

          <span className="flex justify-between text-xs text-muted">
            <span>Predictable</span>

            <span>Wild</span>
          </span>

          <span className="text-xs text-muted">{dialHint(dial)}</span>
        </label>

        <Button onClick={generate} disabled={generating}>
          {generating ? <Spinner small label="Generating" /> : <Sparkles size={16} aria-hidden="true" />}
          {generating ? 'Generating…' : 'Generate'}
        </Button>

        {error && <ErrorText>{error}</ErrorText>}

        {notice && <p className="text-sm text-muted">{notice}</p>}

        {result && (
          <div className="flex flex-col gap-3 rounded-xl border border-border p-3">
            <p className="text-[15px] leading-snug whitespace-pre-line">{result.text}</p>

            <p className="text-xs text-muted">{formatCount(result.tokens.input + result.tokens.output)} tokens used</p>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              {result.kind === 'title' && (
                <Button variant="link" className="text-sm" onClick={() => accept(onUseTitle)}>
                  Use as title
                </Button>
              )}

              {result.kind !== 'title' && (
                <Button variant="link" className="text-sm" onClick={() => accept(onAddToLyrics)}>
                  Add to lyrics
                </Button>
              )}

              {result.kind === 'fragment' && (
                <Button variant="link" className="text-sm" onClick={saveAsFragment} disabled={saving}>
                  Save as fragment
                </Button>
              )}

              <Button variant="quiet" className="text-sm" onClick={() => setResult(null)}>
                Discard
              </Button>
            </div>
          </div>
        )}

        {budget && <TokenMeter budget={budget} />}
      </div>
    </section>
  )
}

/** A thin bar and a line of text showing how much of today's AI budget is left. */
function TokenMeter({ budget }: { budget: TokenBudget }) {
  const percentLeft = budget.limit > 0 ? Math.round((budget.remaining / budget.limit) * 100) : 0

  return (
    <div className="flex flex-col gap-1.5">
      <div className="h-1.5 overflow-hidden rounded-full bg-border">
        <div className="h-full rounded-full bg-primary" style={{ width: `${percentLeft}%` }} />
      </div>

      <p className="text-xs text-muted">
        {formatCount(budget.remaining)} of {formatCount(budget.limit)} tokens left today
      </p>
    </div>
  )
}
