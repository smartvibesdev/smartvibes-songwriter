import type { ComponentProps, TextareaHTMLAttributes } from 'react'
import { cx } from './cx'

const FIELD =
  'w-full rounded-2xl border border-border bg-card px-4 py-3 text-foreground outline-none transition ' +
  'placeholder:text-muted focus:border-primary-text focus:ring-2 focus:ring-primary-text/30'

export function TextInput({ className, ...rest }: ComponentProps<'input'>) {
  return <input className={cx(FIELD, className)} {...rest} />
}

export function TextArea({ className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cx(FIELD, 'resize-y', className)} {...rest} />
}
