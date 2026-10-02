import { SignInForm } from './SignInForm'
import { Card } from './ui/Card'
import { Logo } from './ui/Logo'
import { ThemeToggle } from './ui/ThemeToggle'

type SignInPageProps = {
  onSignedIn: () => void
  notice: string
}

/** The signed-out screen: a centered card with the sign-in form. */
export function SignInPage({ onSignedIn, notice }: SignInPageProps) {
  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col gap-10 px-6 py-8">
      <header className="flex items-center justify-between">
        <Logo />

        <ThemeToggle />
      </header>

      <main className="my-auto pb-16">
        <Card>
          <SignInForm onSignedIn={onSignedIn} notice={notice} />
        </Card>
      </main>
    </div>
  )
}
