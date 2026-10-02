import { Shuffle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { type Fragment, randomFragments } from '../api'
import { describeError } from '../errors'
import { hashTags } from '../tags'
import { Button } from '../ui/Button'

/** One random fragment, or null if there are none. `excludeId` is a fragment to avoid. */
async function fetchRandom(excludeId?: string): Promise<Fragment | null> {
  const picked = await randomFragments({ exclude: excludeId })

  return picked[0] ?? null
}

/** The big cobalt card on Explore: one random fragment, and a button for another. */
export function RandomFragmentCard() {
  const [fragment, setFragment] = useState<Fragment | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function pickAnother(currentId?: string) {
    setBusy(true)
    setError('')

    try {
      setFragment(await fetchRandom(currentId))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setBusy(false)
    }
  }

  // The first pick, when the card appears.
  useEffect(() => {
    fetchRandom()
      .then(setFragment)
      .catch((err) => setError(describeError(err)))
      .finally(() => setLoaded(true))
  }, [])

  function renderBody() {
    if (error) {
      return <p role="alert">{error}</p>
    }

    if (fragment) {
      return (
        <>
          <p className="font-display text-3xl leading-snug font-medium sm:text-[34px]">&ldquo;{fragment.text}&rdquo;</p>

          {fragment.tags.length > 0 && <p className="text-[15px] text-hero-muted">{hashTags(fragment.tags)}</p>}
        </>
      )
    }

    if (loaded) {
      return <p className="text-xl">No fragments yet. Add one and it will show up here.</p>
    }

    return <p className="text-xl text-hero-muted">Finding something&hellip;</p>
  }

  return (
    <section className="flex flex-col gap-8 rounded-[2rem] bg-primary p-8 text-hero-foreground sm:flex-row sm:items-end sm:justify-between sm:p-12">
      <div className="flex max-w-xl flex-col gap-4">
        <p className="text-[13px] font-semibold tracking-[0.12em] text-hero-muted uppercase">Random fragment</p>

        {renderBody()}
      </div>

      <Button variant="accent" onClick={() => pickAnother(fragment?.id)} disabled={busy} className="shrink-0">
        <Shuffle size={18} aria-hidden="true" />
        Another one
      </Button>
    </section>
  )
}
