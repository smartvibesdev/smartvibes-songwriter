import type { HTMLAttributes } from 'react'
import { cx } from './cx'

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cx('rounded-3xl border border-border bg-card p-6 shadow-card sm:p-8', className)} {...rest} />
}
