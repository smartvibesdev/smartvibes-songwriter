import type { ReactNode } from 'react'

/** An error message, announced to screen readers. */
export function ErrorText({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="text-danger-text">
      {children}
    </p>
  )
}
