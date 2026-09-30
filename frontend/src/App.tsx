import { type FormEvent, useEffect, useState } from 'react'
import { confirmSignUp, getIdToken, signIn, signOut, signUp } from './auth'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

type Mode = 'signIn' | 'signUp' | 'confirm'

function App() {
  const [health, setHealth] = useState('checking...')
  const [signedIn, setSignedIn] = useState(false)
  const [mode, setMode] = useState<Mode>('signIn')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [message, setMessage] = useState('')
  const [me, setMe] = useState('')

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then((d) => setHealth(d.status))
      .catch(() => setHealth('unreachable'))
    getIdToken().then((token) => setSignedIn(token !== null))
  }, [])

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
        setSignedIn(true)
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err))
    }
  }

  async function callMe() {
    const token = await getIdToken()
    if (!token) {
      setSignedIn(false)
      return
    }
    const r = await fetch(`${API_URL}/me`, { headers: { Authorization: `Bearer ${token}` } })
    setMe(`${r.status} ${await r.text()}`)
  }

  return (
    <main>
      <h1>SmartVibes Songwriter</h1>
      <p>API status: {health}</p>

      {signedIn ? (
        <>
          <button onClick={callMe}>Call /me</button>{' '}
          <button
            onClick={() => {
              signOut()
              setSignedIn(false)
              setMe('')
            }}
          >
            Sign out
          </button>
          {me && <pre>{me}</pre>}
        </>
      ) : (
        <form onSubmit={submit}>
          <h2>{mode === 'signIn' ? 'Sign in' : mode === 'signUp' ? 'Create account' : 'Verify email'}</h2>
          <p>
            <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </p>
          {mode !== 'confirm' && (
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
          <button type="submit">{mode === 'signIn' ? 'Sign in' : mode === 'signUp' ? 'Sign up' : 'Confirm'}</button>{' '}
          {mode === 'signIn' && (
            <button type="button" onClick={() => setMode('signUp')}>
              Create account
            </button>
          )}
          {message && <p>{message}</p>}
        </form>
      )}
    </main>
  )
}

export default App
