import { useEffect, useState } from 'react'
import { type Fragment, randomFragments } from '../api'
import { describeError } from '../errors'

/** One random fragment, or null if there are none. `excludeId` is a fragment to avoid. */
async function fetchRandom(excludeId?: string): Promise<Fragment | null> {
  const picked = await randomFragments({ exclude: excludeId })

  return picked[0] ?? null
}

/** A random fragment for Home, picked when this first runs, and a function to pick another. */
export function useRandomFragment() {
  const [fragment, setFragment] = useState<Fragment | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function pickAnother() {
    setBusy(true)
    setError('')

    try {
      setFragment(await fetchRandom(fragment?.id))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setBusy(false)
    }
  }

  // The first pick. If this effect runs again (as it does twice on purpose in the dev server's
  // Strict Mode) before the answer comes, the answer is dropped.
  useEffect(() => {
    let active = true

    fetchRandom()
      .then((picked) => {
        if (active) {
          setFragment(picked)
        }
      })
      .catch((err) => {
        if (active) {
          setError(describeError(err))
        }
      })
      .finally(() => {
        if (active) {
          setLoaded(true)
        }
      })

    return () => {
      active = false
    }
  }, [])

  return { fragment, loaded, busy, error, pickAnother }
}
