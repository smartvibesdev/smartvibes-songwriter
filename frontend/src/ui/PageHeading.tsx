type PageHeadingProps = { title: string; subtitle?: string }

export function PageHeading({ title, subtitle }: PageHeadingProps) {
  return (
    <header className="flex flex-col gap-3">
      <h1 className="font-display text-5xl leading-none font-semibold">{title}</h1>

      {subtitle && <p className="text-lg text-muted">{subtitle}</p>}
    </header>
  )
}
