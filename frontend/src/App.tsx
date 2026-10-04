import { useEffect, useState } from 'react'
import { BrowserRouter } from 'react-router'
import { AppShell } from './AppShell'
import { completeOAuthSignIn, getIdToken } from './auth'
import { describeError } from './errors'
import { SignInPage } from './SignInPage'
import { AppStateProvider } from './state/AppStateProvider'

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
    return (
      <BrowserRouter>
        <AppStateProvider>
          <AppShell onSignedOut={() => setSession('signedOut')} />
        </AppStateProvider>
      </BrowserRouter>
    )
  }

  if (session === 'signedOut') {
    return <SignInPage onSignedIn={() => setSession('signedIn')} notice={notice} />
  }

  // Still checking for a saved session: show nothing, so the sign-in form does not flash.
  return null
}

export default App
