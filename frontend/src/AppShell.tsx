import { useState } from 'react'
import { signOut } from './auth'
import { HomePage } from './pages/HomePage'
import { Button } from './ui/Button'
import { Logo } from './ui/Logo'
import { ThemeToggle } from './ui/ThemeToggle'

type AppShellProps = {
  /** Called after the user signs out. */
  onSignedOut: () => void
}

/** What a signed-in user sees: the header, and the Home page below it. */
export function AppShell({ onSignedOut }: AppShellProps) {
  const [signingOut, setSigningOut] = useState(false)

  async function handleSignOut() {
    setSigningOut(true)
    await signOut()
    onSignedOut()
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-[1040px] flex-col gap-14 px-6 py-8 sm:px-10 lg:h-dvh lg:gap-5 lg:py-5">
      <header className="flex flex-wrap items-center justify-between gap-x-6 gap-y-4">
        <div className="flex flex-wrap items-center gap-x-10 gap-y-3">
          <Logo />

          <nav aria-label="Pages" className="flex gap-9">
            <span
              aria-current="page"
              className="border-b-2 border-accent py-1.5 text-base font-semibold text-foreground"
            >
              Home
            </span>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <ThemeToggle />

          <Button variant="quiet" onClick={handleSignOut} disabled={signingOut}>
            Sign out
          </Button>
        </div>
      </header>

      <main className="pb-16 lg:min-h-0 lg:flex-1 lg:pb-0">
        <HomePage />
      </main>
    </div>
  )
}
