import {
  AuthenticationDetails,
  CognitoUser,
  CognitoUserAttribute,
  CognitoUserPool,
  type CognitoUserSession,
} from 'amazon-cognito-identity-js'

const pool = new CognitoUserPool({
  UserPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID ?? '',
  ClientId: import.meta.env.VITE_COGNITO_CLIENT_ID ?? '',
})

// Google sign-in goes through Cognito's hosted domain (authorization code flow
// with PKCE). The resulting tokens are kept in localStorage.
const COGNITO_DOMAIN = import.meta.env.VITE_COGNITO_DOMAIN ?? ''
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID ?? ''
const REDIRECT_URI = `${window.location.origin}/`
const TOKENS_KEY = 'sv_oauth_tokens'
const VERIFIER_KEY = 'sv_pkce_verifier'
const STATE_KEY = 'sv_oauth_state'

type OAuthTokens = { idToken: string; refreshToken?: string; expiresAt: number }

const userFor = (email: string) => new CognitoUser({ Username: email, Pool: pool })

export function signUp(email: string, password: string): Promise<void> {
  return new Promise((resolve, reject) => {
    pool.signUp(email, password, [new CognitoUserAttribute({ Name: 'email', Value: email })], [], (err) =>
      err ? reject(err) : resolve(),
    )
  })
}

export function confirmSignUp(email: string, code: string): Promise<void> {
  return new Promise((resolve, reject) => {
    userFor(email).confirmRegistration(code, true, (err) => (err ? reject(err) : resolve()))
  })
}

export function signIn(email: string, password: string): Promise<CognitoUserSession> {
  return new Promise((resolve, reject) => {
    userFor(email).authenticateUser(new AuthenticationDetails({ Username: email, Password: password }), {
      onSuccess: resolve,
      onFailure: reject,
    })
  })
}

/**
 * Sign out. Always clears the tokens held in this browser. If the user signed in
 * with Google, also visits Cognito's /logout endpoint, which ends the Cognito
 * session on the hosted domain (otherwise "Sign in with Google" could log them
 * straight back in). It does not sign them out of Google itself, and the page
 * navigates away, so call this last.
 */
export function signOut(): void {
  pool.getCurrentUser()?.signOut()
  const wasFederated = readTokens() !== null
  try {
    localStorage.removeItem(TOKENS_KEY)
  } catch {
    /* storage unavailable */
  }
  if (wasFederated && COGNITO_DOMAIN) {
    const params = new URLSearchParams({ client_id: CLIENT_ID, logout_uri: REDIRECT_URI })
    window.location.assign(`https://${COGNITO_DOMAIN}/logout?${params}`)
  }
}

const base64Url = (bytes: Uint8Array) =>
  btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')

function readTokens(): OAuthTokens | null {
  try {
    const raw = localStorage.getItem(TOKENS_KEY)
    return raw ? (JSON.parse(raw) as OAuthTokens) : null
  } catch {
    return null
  }
}

function storeTokens(t: { id_token: string; refresh_token?: string; expires_in: number }, previous?: OAuthTokens) {
  const tokens: OAuthTokens = {
    idToken: t.id_token,
    refreshToken: t.refresh_token ?? previous?.refreshToken,
    expiresAt: Date.now() + t.expires_in * 1000,
  }
  localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens))
}

async function tokenRequest(body: Record<string, string>) {
  const r = await fetch(`https://${COGNITO_DOMAIN}/oauth2/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ client_id: CLIENT_ID, ...body }),
  })
  if (!r.ok) throw new Error(`Token request failed (${r.status})`)
  return r.json()
}

/** Redirect the browser to Cognito's hosted sign-in, going straight to Google. */
export async function signInWithGoogle(): Promise<void> {
  const verifier = base64Url(crypto.getRandomValues(new Uint8Array(48)))
  const challenge = base64Url(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))))
  const state = base64Url(crypto.getRandomValues(new Uint8Array(16)))
  sessionStorage.setItem(VERIFIER_KEY, verifier)
  sessionStorage.setItem(STATE_KEY, state)
  const params = new URLSearchParams({
    identity_provider: 'Google',
    response_type: 'code',
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    scope: 'openid email profile',
    state,
    code_challenge: challenge,
    code_challenge_method: 'S256',
  })
  window.location.assign(`https://${COGNITO_DOMAIN}/oauth2/authorize?${params}`)
}

/**
 * Call once on page load. If the URL holds a sign-in result from Cognito
 * (?code=...), exchange it for tokens and clean the URL. Returns true if it
 * completed a Google sign-in; throws if Cognito returned an error.
 */
export async function completeOAuthSignIn(): Promise<boolean> {
  const params = new URLSearchParams(window.location.search)
  const error = params.get('error_description') ?? params.get('error')
  const code = params.get('code')
  if (!code && !error) return false
  window.history.replaceState({}, '', window.location.pathname)
  if (error) throw new Error(error)
  const verifier = sessionStorage.getItem(VERIFIER_KEY)
  const expectedState = sessionStorage.getItem(STATE_KEY)
  sessionStorage.removeItem(VERIFIER_KEY)
  sessionStorage.removeItem(STATE_KEY)
  if (!verifier || !code || params.get('state') !== expectedState) throw new Error('Sign-in response did not match this browser session')
  storeTokens(await tokenRequest({ grant_type: 'authorization_code', code, redirect_uri: REDIRECT_URI, code_verifier: verifier }))
  return true
}

async function getFederatedIdToken(): Promise<string | null> {
  const tokens = readTokens()
  if (!tokens) return null
  if (tokens.expiresAt - Date.now() > 60_000) return tokens.idToken
  if (!tokens.refreshToken) return null
  try {
    storeTokens(await tokenRequest({ grant_type: 'refresh_token', refresh_token: tokens.refreshToken }), tokens)
    return readTokens()?.idToken ?? null
  } catch {
    localStorage.removeItem(TOKENS_KEY)
    return null
  }
}

/** The signed-in user's ID token (refreshed automatically if expired), or null. */
export async function getIdToken(): Promise<string | null> {
  const federated = await getFederatedIdToken()
  if (federated) return federated
  return new Promise((resolve) => {
    const user = pool.getCurrentUser()
    if (!user) return resolve(null)
    user.getSession((err: Error | null, session: CognitoUserSession | null) =>
      resolve(err || !session?.isValid() ? null : session.getIdToken().getJwtToken()),
    )
  })
}
