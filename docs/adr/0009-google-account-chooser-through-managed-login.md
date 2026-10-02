# 0009. Google account chooser through Cognito managed login

- Status: Accepted
- Date: 2026-10-02

## Context

After a user signs out of the app and clicks "Sign in with Google", Google
signed them straight back in with no prompt. Signing out of the app ends the app's
session and Cognito's hosted session (via `/logout`), but not the user's own
Google session. AWS documents this: the `/logout` endpoint "doesn't sign users
out of OIDC or social identity providers". It is normal single sign-on
behavior, but it surprised the owner. On a shared computer, the next person to
click "Sign in with Google" would be signed in as the previous user.

Cognito's authorize endpoint has a `prompt` parameter that it forwards to
Google, so `prompt=select_account` makes Google show its account chooser. The
documentation says `prompt` is available only with the managed login branding
version, not the classic hosted UI. The dev domain reported
`ManagedLoginVersion: 1` (classic).

## Options considered

- **Leave it.** Standard SSO behavior, no change. Rejected: it feels wrong to
  the owner and is a poor experience on shared computers.
- **Send users to Google's own sign-out page when they sign out.** Signs them out
  of Google everywhere, which would surprise users.
- **Switch the domain to managed login and send `prompt=select_account`.**
  Cognito forwards the prompt to Google, which shows its account chooser. Needs
  the Essentials or Plus feature plan (the pool is on Essentials) and a
  branding style for the app client.
- **Build Google sign-in outside Cognito.** A large change that gives up the
  Cognito integration the app relies on.

## Decision

- Set the user pool domain to the newer managed login
  (`ManagedLoginVersion.NEWER_MANAGED_LOGIN`) in the CDK stack, and add a
  `CfnManagedLoginBranding` for the web app client using Cognito's default
  values. Users go straight to Google and rarely see Cognito's own pages, so
  custom branding can wait for the UI pass.
- `signInWithGoogle` adds `prompt=select_account` to the authorize request.
- Email and password sign-in is unchanged: it uses the Cognito SDK directly and
  does not use the hosted pages.

## Consequences

- After signing out, "Sign in with Google" shows Google's account chooser. The
  user still picks an account, and may not need a password if Google's session
  is still active. This is the strongest prompt Google documents for this case.
  `prompt=login`, which would force a fresh sign-in, is not used because it is not
  one of the values Google documents.
- Switching versions changes how long hosted-page sessions last: AWS says
  Cognito does not maintain user sessions across the switch. Existing Google
  users may have to sign in once more. Whether refresh tokens are affected has
  not been verified.
- The pool must stay on the Essentials or Plus plan. The `dev` pool is on
  Essentials. The `prod` pool's plan has not been checked and must be confirmed
  before `prod` is deployed.
- The change is an in-place update of the domain plus one new resource, shown by
  `cdk diff` against `dev`. It has not been deployed or tried in a browser.
