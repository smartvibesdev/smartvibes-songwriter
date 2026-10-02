import type { ButtonHTMLAttributes } from 'react'
import { cx } from './cx'

type Variant = 'primary' | 'accent' | 'outline' | 'danger' | 'link' | 'quiet'

const BOX = 'rounded-2xl px-5 py-3 font-semibold'

const VARIANTS: Record<Variant, string> = {
  primary: `${BOX} bg-primary text-primary-foreground hover:opacity-90`,
  accent: `${BOX} bg-accent text-accent-foreground hover:opacity-90`,
  outline: `${BOX} border border-border bg-card text-foreground hover:border-muted`,
  danger: `${BOX} bg-destructive text-destructive-foreground hover:opacity-90`,
  // Text-only buttons, for actions inside a card (Edit, Delete, Sign out).
  link: 'font-semibold text-primary-text hover:underline',
  quiet: 'font-medium text-muted hover:text-foreground',
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }

export function Button({ variant = 'primary', type = 'button', className, ...rest }: ButtonProps) {
  return (
    <button
      type={type}
      className={cx(
        'inline-flex cursor-pointer items-center justify-center gap-2 text-[15px] transition',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-text',
        'disabled:cursor-not-allowed disabled:opacity-50',
        VARIANTS[variant],
        className,
      )}
      {...rest}
    />
  )
}
