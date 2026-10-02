import { useEffect, useState } from 'react'
import { AppShell } from './AppShell'
import { completeOAuthSignIn, getIdToken } from './auth'
import { describeError } from './errors'
import { SignInPage } from './SignInPage'

type Session = 'checking' | 'signedIn' | 'signedOut'

function App() {
  const [session, setSession] = useState<Session>('checking')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    completeOAuthSignIn()
      .catch((err) => setNotice(describeError(err)))
      .then(() => getIdToken())
      .then((token) => setSession(token ? 'signedIn' : 'signedOut'))
  }, [])

  if (session === 'signedIn') {
    return <AppShell onSignedOut={() => setSession('signedOut')} />
  }

  if (session === 'signedOut') {
    return <SignInPage onSignedIn={() => setSession('signedIn')} notice={notice} />
  }

  // Still checking for a saved session: show nothing, so the sign-in form does not flash.
  return null
}

export default App
