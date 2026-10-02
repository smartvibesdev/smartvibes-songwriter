import { ChevronDown } from 'lucide-react'
import type { SelectHTMLAttributes } from 'react'
import { cx } from './cx'

/**
 * A dropdown with our own arrow. The browser's built-in arrow sits hard against the right edge,
 * so it is hidden and the same arrow as the New button is drawn with room around it.
 */
export function Select({ className, children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className="relative">
      <select
        className={cx(
          'cursor-pointer appearance-none rounded-xl border border-border bg-card py-2.5 pr-10 pl-3 text-sm text-foreground',
          className,
        )}
        {...rest}
      >
        {children}
      </select>

      <ChevronDown
        size={16}
        aria-hidden="true"
        className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-muted"
      />
    </div>
  )
}
