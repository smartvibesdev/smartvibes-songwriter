import { useState } from 'react'
import { signOut } from './auth'
import { HomePage } from './pages/HomePage'
import { AccountMenu } from './ui/AccountMenu'
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
      <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-4 sm:gap-x-6">
        <div className="flex items-center gap-x-5 sm:gap-x-10">
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
        <HomePage />
      </main>
    </div>
  )
}
