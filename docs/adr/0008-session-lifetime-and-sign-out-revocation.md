# 0008. Session lifetime and sign-out revocation

- Status: Accepted
- Date: 2026-10-01

## Context

A signed-in browser holds three Cognito tokens in local storage. The ID and
access tokens last 1 hour and are what API Gateway checks on each request. The
refresh token quietly gets new ones, so the user stays signed in. Cognito's
default refresh token lifetime is 30 days, and the app client had no override.
Testing showed a Week 1 sign-in still active a day later with no prompt.

Two things made that worth a decision:

- A copied refresh token keeps working for its whole lifetime, so the lifetime
  is how long a stolen session stays useful.
- Signing out only cleared the browser's copy. The library's `signOut()` does
  not tell Cognito to cancel the token unless it is given a callback, and the
  Google path never called Cognito's revoke endpoint. A copied refresh token
  still worked after the user clicked Sign out.

This is a portfolio app holding song lyrics, so the aim is sound, proportionate
practice, not maximum hardening.

## Options considered

- **Keep the 30-day default.** No work, but a long window, and the sign-out gap
  above stays.
- **Shorten the refresh token** (1 day, 7 days). One line in the CDK stack. A
  1-day lifetime fits browser-app guidance best but means signing in daily.
  7 days is a reasonable middle.
- **Refresh token rotation.** AWS recommends it: each refresh cancels the old
  token and issues a new one, so a stolen token is detected and dies quickly.
  It is not compatible with `REFRESH_TOKEN_AUTH`, the refresh method the
  `amazon-cognito-identity-js` library uses for email sign-in. Using it would
  mean replacing the library's refresh with our own calls to
  `GetTokensFromRefreshToken`, a real rewrite of sign-in. The Google path
  already copes with rotation, because `auth.ts` accepts a new refresh token.
- **Keep tokens out of local storage** (in memory, or HttpOnly cookies behind a
  small backend). Stronger against script injection, but a larger redesign and
  not worth it for this data.
- **Revoke on sign-out.** Cognito supports it (`/oauth2/revoke`, and the
  library's `signOut` with a callback). It needs token revocation enabled on
  the app client, which it is.

## Decision

- **Refresh token lifetime: 7 days**, set in the CDK stack
  (`refresh_token_validity`), for both environments. Rotation does not extend
  it, so a session ends 7 days after sign-in.
- **Sign-out revokes the refresh token**, then clears the browser's copy. Email
  sign-ins use the library's `signOut` with a callback. Google sign-ins call
  `/oauth2/revoke` directly, then visit `/logout` as before. Revocation is best
  effort with a 5-second limit: if Cognito cannot be reached, the user is still
  signed out locally.
- **Not adopted for now:** refresh token rotation, and moving tokens out of
  local storage. Both are the production answer and are recorded here as the
  next steps if the app ever held sensitive data.

## Consequences

- A stolen refresh token is useful for at most 7 days, and not at all after the
  real owner signs out (provided the revoke call reached Cognito).
- Users sign in again at least once a week.
- Tokens in local storage can still be read by script running on the page. A
  cross-site scripting bug would expose them. Rendering all user text as plain
  text (the app's rule) is the main defence.
- Sessions already open when this ships keep their original expiry until the
  user signs out and in again. This is expected behavior but has not been
  verified.
- On the Google path, the browser's preflight request to `/oauth2/revoke` was
  checked against the dev domain and allowed, but the full revoke-then-reject
  sequence needs a manual check on `dev`: sign out, then confirm the old refresh
  token no longer refreshes.
