export function Logo() {
  return (
    <div className="flex items-center gap-3 font-display text-[22px] font-semibold">
      <div className="size-7 rounded-[9px] bg-accent" aria-hidden="true" />
      {/* Phones show only the mark; the name stays for screen readers. */}
      <span className="sr-only sm:not-sr-only">SmartVibes</span>
    </div>
  )
}
