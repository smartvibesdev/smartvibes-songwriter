type PageHeadingProps = { title: string; subtitle?: string }

export function PageHeading({ title, subtitle }: PageHeadingProps) {
  return (
    <header className="flex flex-col gap-3 lg:flex-row lg:items-baseline lg:gap-4">
      <h1 className="font-display text-5xl leading-none font-semibold lg:text-4xl">{title}</h1>

      {subtitle && <p className="text-lg text-muted lg:text-base">{subtitle}</p>}
    </header>
  )
}
