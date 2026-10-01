import { useEffect, useState } from 'react'
import { completeOAuthSignIn, getIdToken } from './auth'
import { describeError } from './errors'
import { Home } from './Home'
import { SignInForm } from './SignInForm'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function App() {
  const [health, setHealth] = useState('checking...')
  const [signedIn, setSignedIn] = useState(false)
  const [notice, setNotice] = useState('')

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then((d) => setHealth(d.status))
      .catch(() => setHealth('unreachable'))

    completeOAuthSignIn()
      .catch((err) => setNotice(describeError(err)))
      .then(() => getIdToken())
      .then((token) => setSignedIn(Boolean(token)))
  }, [])

  return (
    <main>
      <h1>SmartVibes Songwriter</h1>
      <p>API status: {health}</p>

      {signedIn ? (
        <Home onSignedOut={() => setSignedIn(false)} />
      ) : (
        <SignInForm onSignedIn={() => setSignedIn(true)} notice={notice} />
      )}
    </main>
  )
}

export default App
