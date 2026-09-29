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

export function signOut(): void {
  pool.getCurrentUser()?.signOut()
}

/** The signed-in user's ID token (refreshed automatically if expired), or null. */
export function getIdToken(): Promise<string | null> {
  return new Promise((resolve) => {
    const user = pool.getCurrentUser()
    if (!user) return resolve(null)
    user.getSession((err: Error | null, session: CognitoUserSession | null) =>
      resolve(err || !session?.isValid() ? null : session.getIdToken().getJwtToken()),
    )
  })
}
