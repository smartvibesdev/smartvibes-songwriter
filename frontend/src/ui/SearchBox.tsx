import { Search, X } from 'lucide-react'

type SearchBoxProps = {
  value: string
  onChange: (value: string) => void
  /** What screen readers call the box. */
  label: string
  placeholder: string
}

/** The big search box at the top of every page, with a small × to clear it. */
export function SearchBox({ value, onChange, label, placeholder }: SearchBoxProps) {
  return (
    <div className="flex min-w-64 flex-1 items-center gap-3.5 rounded-[1.25rem] border border-border bg-card px-6 shadow-card focus-within:border-primary-text focus-within:ring-2 focus-within:ring-primary-text/30">
      <Search size={20} className="text-muted" aria-hidden="true" />

      <input
        aria-label={label}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxLength={100}
        className="w-full bg-transparent py-5 text-lg text-foreground outline-none placeholder:text-muted lg:py-3"
      />

      {value && (
        <button
          type="button"
          aria-label="Clear search"
          onClick={() => onChange('')}
          className="cursor-pointer rounded-full p-1 text-muted hover:text-foreground"
        >
          <X size={18} />
        </button>
      )}
    </div>
  )
}
