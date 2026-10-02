import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../theme'
import { Button } from './Button'

/** A button that flips between light and dark mode. */
export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  const label = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'

  return (
    <Button variant="quiet" onClick={toggleTheme} aria-label={label} title={label} className="p-2">
      {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
    </Button>
  )
}
