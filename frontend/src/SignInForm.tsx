import { type FormEvent, useState } from 'react'
import { confirmSignUp, signIn, signInWithGoogle, signUp } from './auth'
import { describeError } from './errors'
import { Button } from './ui/Button'
import { TextInput } from './ui/fields'

type Mode = 'signIn' | 'signUp' | 'confirm'

const HEADINGS: Record<Mode, string> = {
  signIn: 'Welcome back',
  signUp: 'Create your account',
  confirm: 'Check your email',
}

const SUBMIT_LABELS: Record<Mode, string> = {
  signIn: 'Sign in',
  signUp: 'Sign up',
  confirm: 'Confirm',
}

type SignInFormProps = {
  /** Called after a successful email and password sign-in. */
  onSignedIn: () => void
  /** A message from outside the form, such as a failed Google sign-in. */
  notice: string
}

export function SignInForm({ onSignedIn, notice }: SignInFormProps) {
  const [mode, setMode] = useState<Mode>('signIn')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [message, setMessage] = useState('')

  const showPasswordField = mode === 'signIn' || mode === 'signUp'

  async function submit(e: FormEvent) {
    e.preventDefault()
    setMessage('')

    try {
      if (mode === 'signUp') {
        await signUp(email, password)
        setMode('confirm')
        setMessage('Check your email for a verification code.')
      } else if (mode === 'confirm') {
        await confirmSignUp(email, code)
        setMode('signIn')
        setMessage('Email confirmed. Please sign in.')
      } else {
        await signIn(email, password)
        onSignedIn()
      }
    } catch (err) {
      setMessage(describeError(err))
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-5">
      <h1 className="font-display text-3xl font-semibold">{HEADINGS[mode]}</h1>

      <TextInput
        type="email"
        aria-label="Email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />

      {showPasswordField && (
        <TextInput
          type="password"
          aria-label="Password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      )}

      {mode === 'confirm' && (
        <TextInput
          aria-label="Verification code"
          placeholder="Verification code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          required
        />
      )}

      <Button type="submit">{SUBMIT_LABELS[mode]}</Button>

      {mode === 'signIn' && (
        <div className="flex flex-col items-center gap-3">
          <Button variant="outline" onClick={() => signInWithGoogle()} className="w-full">
            Continue with Google
          </Button>

          <Button variant="quiet" onClick={() => setMode('signUp')}>
            Create an account
          </Button>
        </div>
      )}

      {mode === 'signUp' && (
        <Button variant="quiet" onClick={() => setMode('signIn')}>
          I already have an account
        </Button>
      )}

      {notice && (
        <p role="alert" className="text-sm text-soft">
          {notice}
        </p>
      )}

      {message && (
        <p role="alert" className="text-sm text-soft">
          {message}
        </p>
      )}
    </form>
  )
}
