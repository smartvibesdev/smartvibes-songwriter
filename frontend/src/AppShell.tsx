import { useState } from 'react'
import { signOut } from './auth'
import { ExplorePage } from './pages/ExplorePage'
import { FragmentsPage } from './pages/FragmentsPage'
import { SongsPage } from './pages/SongsPage'
import { Button } from './ui/Button'
import { cx } from './ui/cx'
import { Logo } from './ui/Logo'
import { ThemeToggle } from './ui/ThemeToggle'

type Page = 'songs' | 'fragments' | 'explore'

const PAGES: { id: Page; label: string }[] = [
  { id: 'songs', label: 'Songs' },
  { id: 'fragments', label: 'Fragments' },
  { id: 'explore', label: 'Explore' },
]

type AppShellProps = {
  /** Called after the user signs out. */
  onSignedOut: () => void
}

/** What a signed-in user sees: the header and navigation, and the current page. */
export function AppShell({ onSignedOut }: AppShellProps) {
  const [page, setPage] = useState<Page>('explore')
  const [signingOut, setSigningOut] = useState(false)

  async function handleSignOut() {
    setSigningOut(true)
    await signOut()
    onSignedOut()
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-[1040px] flex-col gap-14 px-6 py-8 sm:px-10">
      <header className="flex flex-wrap items-center justify-between gap-x-6 gap-y-4">
        <Logo />

        <nav aria-label="Pages" className="order-last flex w-full justify-center gap-9 sm:order-none sm:w-auto">
          {PAGES.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              aria-current={page === id ? 'page' : undefined}
              onClick={() => setPage(id)}
              className={cx(
                'cursor-pointer border-b-2 py-1.5 text-base transition',
                page === id
                  ? 'border-accent font-semibold text-foreground'
                  : 'border-transparent font-medium text-muted',
              )}
            >
              {label}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <ThemeToggle />

          <Button variant="quiet" onClick={handleSignOut} disabled={signingOut}>
            Sign out
          </Button>
        </div>
      </header>

      <main className="pb-16">
        {page === 'songs' && <SongsPage />}
        {page === 'fragments' && <FragmentsPage />}
        {page === 'explore' && <ExplorePage />}
      </main>
    </div>
  )
}
