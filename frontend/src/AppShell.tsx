import { lazy, Suspense, useState } from 'react'
import { Link, NavLink, Navigate, Route, Routes } from 'react-router'
import { signOut } from './auth'
import { HomePage } from './pages/HomePage'
import { AccountMenu } from './ui/AccountMenu'
import { Button } from './ui/Button'
import { Logo } from './ui/Logo'
import { Spinner } from './ui/Spinner'
import { ThemeToggle } from './ui/ThemeToggle'

// The song page holds the text editor, which is large, so it loads only when someone opens it.
const SongEditorPage = lazy(() =>
  import('./pages/SongEditorPage').then((module) => ({ default: module.SongEditorPage })),
)

type AppShellProps = {
  /** Called after the user signs out. */
  onSignedOut: () => void
}

/** What a signed-in user sees: the header, and the page for the current address below it. */
export function AppShell({ onSignedOut }: AppShellProps) {
  const [signingOut, setSigningOut] = useState(false)

  async function handleSignOut() {
    setSigningOut(true)
    await signOut()
    onSignedOut()
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-[1040px] flex-col gap-6 px-6 py-8 sm:gap-14 sm:px-10 lg:h-dvh lg:gap-5 lg:py-5">
      <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-4 sm:gap-x-6">
        <div className="flex items-center gap-x-5 sm:gap-x-10">
          <Link to="/" aria-label="SmartVibes home">
            <Logo />
          </Link>

          <nav aria-label="Pages" className="flex gap-9">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                isActive
                  ? 'border-b-2 border-accent py-1.5 text-base font-semibold text-foreground'
                  : 'border-b-2 border-transparent py-1.5 text-base font-semibold text-muted hover:text-foreground'
              }
            >
              Home
            </NavLink>
          </nav>
        </div>

        <div className="flex items-center gap-1 sm:gap-3">
          <ThemeToggle />

          {/* Wide screens show Sign out; narrow ones put it in the menu button. */}
          <div className="hidden sm:block">
            <Button variant="quiet" onClick={handleSignOut} disabled={signingOut}>
              Sign out
            </Button>
          </div>

          <div className="sm:hidden">
            <AccountMenu onSignOut={handleSignOut} signingOut={signingOut} />
          </div>
        </div>
      </header>

      <main className="pb-16 lg:min-h-0 lg:flex-1 lg:pb-0">
        <Suspense
          fallback={
            <div className="flex justify-center py-16">
              <Spinner />
            </div>
          }
        >
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/songs/new" element={<SongEditorPage />} />
            <Route path="/songs/:id" element={<SongEditorPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}
