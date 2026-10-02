import type { ReactNode } from 'react'
import { cx } from './cx'

type FieldLabelProps = {
  children: ReactNode
  /** Extra classes, such as a negative right margin to pull the controls closer. */
  className?: string
}

/** A small bold label for a row of controls ("TAGS", "YEAR", "SORT"), so it reads as a heading and not an option. */
export function FieldLabel({ children, className }: FieldLabelProps) {
  return (
    <span className={cx('shrink-0 text-xs font-semibold tracking-[0.12em] text-muted uppercase', className)}>
      {children}
    </span>
  )
}
