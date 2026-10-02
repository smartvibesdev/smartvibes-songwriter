import { useEffect, useState } from 'react'
import { describeError } from './errors'

/**
 * Runs `load` when the component appears, and again whenever `refreshKey` changes. `data`
 * stays null until it succeeds; `error` holds the message if it fails. `load` must be a
 * stable function (declared outside the component), or it would run again on every render.
 * An answer that arrives after a newer request was made is dropped.
 */
export function useLoaded<T>(load: () => Promise<T>, refreshKey = 0) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    load()
      .then((loaded) => {
        if (active) {
          setData(loaded)
        }
      })
      .catch((err) => {
        if (active) {
          setError(describeError(err))
        }
      })

    return () => {
      active = false
    }
  }, [load, refreshKey])

  return { data, setData, error }
}
