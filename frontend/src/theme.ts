import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

// Keep the storage key in sync with the script in index.html.
const STORAGE_KEY = 'sv_theme'

/** The theme the user picked with the toggle, or null if they never did. */
function readSavedTheme(): Theme | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)

    if (saved === 'light' || saved === 'dark') {
      return saved
    }

    return null
  } catch {
    return null
  }
}

function systemPrefersDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/**
 * The current color theme and a function to flip it. Until the user flips it, the theme
 * follows the computer's own light or dark setting. After that, their choice is kept.
 */
export function useTheme() {
  const [saved, setSaved] = useState<Theme | null>(readSavedTheme)
  const [systemDark, setSystemDark] = useState(systemPrefersDark)

  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = (event: MediaQueryListEvent) => setSystemDark(event.matches)

    query.addEventListener('change', onChange)

    return () => query.removeEventListener('change', onChange)
  }, [])

  const theme: Theme = saved ?? (systemDark ? 'dark' : 'light')

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  function toggleTheme() {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'

    setSaved(next)

    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      /* storage unavailable: the choice lasts until the page reloads */
    }
  }

  return { theme, toggleTheme }
}
