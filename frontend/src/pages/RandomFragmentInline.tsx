import { Shuffle } from 'lucide-react'
import { hashTags } from '../tags'
import { Button } from '../ui/Button'
import { FieldLabel } from '../ui/FieldLabel'
import { useAppState } from '../state/AppStateContext'

/** A small, quiet random fragment for inspiration, with a button to show another. */
export function RandomFragmentInline() {
  const { fragment, loaded, busy, error, pickAnother } = useAppState().random

  function renderText() {
    if (error) {
      return (
        <p role="alert" className="text-sm text-danger-text">
          {error}
        </p>
      )
    }

    if (fragment) {
      return (
        <p className="line-clamp-2 text-sm leading-snug text-soft" title={fragment.text}>
          &ldquo;{fragment.text}&rdquo;
          {fragment.tags.length > 0 && <span className="text-muted"> {hashTags(fragment.tags)}</span>}
        </p>
      )
    }

    if (loaded) {
      return <p className="text-sm text-muted">No fragments yet.</p>
    }

    return <p className="text-sm text-muted">Finding something&hellip;</p>
  }

  return (
    <div className="flex min-w-0 max-w-md items-center gap-3">
      <div className="flex min-w-0 flex-col gap-1">
        <FieldLabel>Random fragment</FieldLabel>

        {renderText()}
      </div>

      <Button
        variant="quiet"
        className="p-2"
        onClick={pickAnother}
        disabled={busy}
        aria-label="Show another random fragment"
        title="Another one"
      >
        <Shuffle size={18} />
      </Button>
    </div>
  )
}
