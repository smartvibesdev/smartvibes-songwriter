import { useEffect, useState } from 'react'
import { describeError } from './errors'

/**
 * Runs `load` once when the component appears. `data` stays null until it succeeds;
 * `error` holds the message if it fails. `load` must be a stable function (declared
 * outside the component), or it would run again on every render.
 */
export function useLoaded<T>(load: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    load()
      .then(setData)
      .catch((err) => setError(describeError(err)))
  }, [load])

  return { data, setData, error }
}
