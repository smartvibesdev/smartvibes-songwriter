# 0005. Google sign-in through Cognito's hosted domain

- Status: Accepted
- Date: 2026-10-01

## Context

The plan calls for "Sign in with Google" so users do not have to create a
password. Sign-in already works with email and password through an Amazon
Cognito user pool, and API Gateway verifies Cognito tokens before any request
reaches the backend. Whatever is added for Google must produce the same kind of
token, so the backend and the `/me` route do not need to know how someone
signed in.

## Options considered

- **Google as an identity provider inside Cognito, using Cognito's hosted
  domain.** The browser sends the user to Cognito, Cognito sends them to
  Google, and Cognito issues its own token afterwards. Same token, same API
  authorizer, no backend change. Needs a Cognito domain per environment and a
  Google OAuth client.
- **Google Identity Services directly in the browser, and verify Google's
  token in the backend.** No Cognito domain, but a second kind of token to
  verify, a custom authorizer, and separate handling in every route.
- **A hosted auth service (Auth0, Clerk and similar).** Less code, but moves
  sign-in out of AWS and adds a vendor and a bill, which cuts against the
  portfolio goal of showing the AWS work.
- **A client library (such as AWS Amplify) for the browser side.** Handles the
  redirect and token exchange, but pulls in a large dependency for one flow.

## Decision

Use Google as a Cognito identity provider, through each environment's Cognito
hosted domain (`smartvibes-songwriter-<env>`). The frontend implements the
OAuth authorization code flow with PKCE (a one-time proof sent with the
request, so an intercepted code is useless) in a small amount of code of its
own, with no new dependency.

One Google OAuth client is shared by all environments, with each
environment's Cognito return address registered on it. The Google client secret
is never committed: it lives in AWS Secrets Manager, in each account, under the
name `smartvibes-songwriter/google-oauth-client-secret`, and CloudFormation
reads it when the stack is deployed. The Google client ID is public and is in
the infrastructure code.

## Consequences

- **One kind of token.** Google users and email/password users both get Cognito
  tokens, so the authorizer and `/me` are unchanged.
- **Separate users.** A person who signs in with Google and one who signs up by
  email with the same address become two different Cognito users. They are not
  linked. Linking them would need a Cognito trigger (a small Lambda) and is
  deferred.
- **A secret to manage in each account.** The deploy fails if the secret does
  not exist in that account, and rotating the Google secret means updating both
  accounts.
- **A globally unique domain name per environment.** Cognito domain prefixes
  are unique across all of AWS, so a name can be taken. If so, rename it in the
  stack and in the Google client's return addresses.
- **Google app stays in "Testing" mode.** Only listed test users can sign in
  with Google, and Google shows an unverified-app warning. Opening it to the
  public needs Google's app verification.
- **Tokens are kept in the browser's local storage.** Simple, and the same as
  the email sign-in library does, but readable by any script injected into the
  page. The risk is reduced by rendering model output as plain text (see the
  security notes in the plan). A cookie-based approach is a possible later
  change.
- **Callback addresses must match exactly,** including the trailing slash. The
  stack registers the site address with a trailing slash, and
  `http://localhost:5173/` for local development.
