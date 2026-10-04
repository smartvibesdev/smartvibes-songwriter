type SpinnerProps = {
  /** Read out by screen readers. */
  label?: string
  className?: string
  /** A smaller ring, for use inside a button. */
  small?: boolean
}

/** A small spinning ring in the primary colour. */
export function Spinner({ label = 'Loading', className = '', small = false }: SpinnerProps) {
  const size = small ? 'size-5' : 'size-9'

  return (
    <span role="status" className={className}>
      <svg className={`${size} animate-spin text-primary-text`} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" className="opacity-20" />
        <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      </svg>

      <span className="sr-only">{label}</span>
    </span>
  )
}
