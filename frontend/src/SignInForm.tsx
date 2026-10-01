import { type FormEvent, useState } from 'react'
import { confirmSignUp, signIn, signInWithGoogle, signUp } from './auth'
import { describeError } from './errors'

type Mode = 'signIn' | 'signUp' | 'confirm'

const HEADINGS: Record<Mode, string> = {
  signIn: 'Sign in',
  signUp: 'Create account',
  confirm: 'Verify email',
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
    <form onSubmit={submit}>
      <h2>{HEADINGS[mode]}</h2>

      <p>
        <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      </p>

      {showPasswordField && (
        <p>
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </p>
      )}

      {mode === 'confirm' && (
        <p>
          <input placeholder="Verification code" value={code} onChange={(e) => setCode(e.target.value)} required />
        </p>
      )}

      <button type="submit">{SUBMIT_LABELS[mode]}</button>

      {mode === 'signIn' && (
        <>
          {' '}
          <button type="button" onClick={() => setMode('signUp')}>
            Create account
          </button>{' '}
          <button type="button" onClick={() => signInWithGoogle()}>
            Sign in with Google
          </button>
        </>
      )}

      {notice && <p>{notice}</p>}
      {message && <p>{message}</p>}
    </form>
  )
}
