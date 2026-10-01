# Deployment notes

How the AWS side of this project is set up and operated. No real IDs or
secrets belong in this file; values for the deployed stack live in
`frontend/.env.local` (git-ignored) and can always be re-read from AWS.

## Where things live

Three AWS accounts in one AWS Organization, all in `us-east-1`:

| Account | CLI profile | Holds |
| ------- | ----------- | ----- |
| Management ("Smart Vibes") | `smartvibes-mgmt` | The organization and IAM Identity Center only. No app resources, apart from `CDKToolkit` (the CDK bootstrap). |
| `smartvibes-dev` | `smartvibes-dev` | The `dev` environment: stack `SmartvibesSongwriter-dev` |
| `smartvibes-prod` | `smartvibes-prod` | The `prod` environment: stack `SmartvibesSongwriter-prod` |

All three profiles use one SSO session, so a single
`aws sso login --profile smartvibes-dev` signs in to all of them.

| Thing | Value |
| ----- | ----- |
| Resource naming | `smartvibes-songwriter-<env>-<resource>` |
| Stateful resources | DynamoDB table and Cognito user pool are `RETAIN` (survive stack deletion) |
| Each account has its own | table, user pool, API, Lambda, site, CDK bootstrap, GitHub deploy role |

`dev` and `prod` share nothing: users, data and URLs are separate. A `test`
environment does not exist yet; if added, give it its own account the same way.

## Automatic deploy (GitHub Actions)

`.github/workflows/deploy.yml` is one workflow that deploys whichever
environment it is given. Each environment deploys into its **own AWS account**,
through a role in that account:

- **Merging to `main` deploys `dev` automatically, with no approval.**
- **To deploy another environment:** GitHub repo > Actions > Deploy > Run
  workflow, then pick `dev` or `prod` (`test` is in the list but has no account).

It signs in to AWS with a short-lived OIDC (OpenID Connect) token, so no AWS
keys are stored in GitHub. Each deploy runs in the GitHub _environment_ of the
same name. The environment holds that environment's variables, including the
ARN (Amazon Resource Name) of the deploy role in its account, and its approval
rule: `dev` has none, so it deploys as soon as it starts; `prod` requires you to
approve first. Only `main` may deploy to either (see
[ADR 0006](adr/0006-deployment-flow-and-branching.md); there is no `develop`
branch and feature branches do not deploy).

### One-time setup per account: bootstrap and deploy role

Run by hand, from `infra/` with the venv active. Use the environment's profile
(`smartvibes-dev` or `smartvibes-prod`) and its `-c env=` value:

```bash
aws sso login --profile smartvibes-dev
cd infra && source .venv/bin/activate
cdk bootstrap aws://<that-account-id>/us-east-1 --profile smartvibes-dev
cdk deploy SmartvibesSongwriter-github -c env=dev --profile smartvibes-dev
# prod: the same two commands with <prod-account-id>, -c env=prod, --profile smartvibes-prod
```

`cdk bootstrap` creates the storage and roles CDK needs in that account. The
`-github` stack creates the OIDC provider and one deploy role that trusts only
that environment's GitHub workflows (`-c env=dev` trusts only the `dev`
environment, `-c env=prod` only `prod`). Copy the `DeployRoleArn` output; its
account number must match the account you intended.

### One-time setup per environment: GitHub environment and variables

1. **Create the environment** in GitHub: repo Settings > Environments > New
   environment, named `dev` or `prod`. Under "Deployment branches and tags",
   allow only `main`. For `prod`, also tick **Required reviewers**, add yourself
   and **click Save protection rules**; leave "Prevent self-review" off. Leave
   reviewers off for `dev`. Create `prod` before its first deploy: if GitHub
   creates it on its own, it has no reviewer and would deploy without asking.
2. **Add variables to that environment** (Settings > Environments > the
   environment > Environment variables). None are secret. The names are the
   same in every environment; the values differ:

   | Variable | Value |
   | -------- | ----- |
   | `AWS_DEPLOY_ROLE_ARN` | that account's `DeployRoleArn` |
   | `VITE_API_URL` | that environment's `ApiUrl` stack output |
   | `VITE_COGNITO_USER_POOL_ID` | that environment's `UserPoolId` output |
   | `VITE_COGNITO_CLIENT_ID` | that environment's `UserPoolClientId` output |
   | `VITE_COGNITO_REGION` | `us-east-1` |
   | `VITE_COGNITO_DOMAIN` | the `CognitoDomain` output, i.e. `smartvibes-songwriter-<env>.auth.us-east-1.amazoncognito.com` |

   For a brand-new environment, its stack outputs don't exist until the stack
   has been deployed once. Deploy it the first time with
   `scripts/new-env.sh <env>` (see "Deploying by hand"), copy the outputs into
   the variables, then run the workflow once to upload the site.

### What happens on each deploy

The workflow waits for the environment's approval (only `prod` has one), checks
that the variables are set, builds the frontend, then runs
`cdk deploy SmartvibesSongwriter-<env> -c env=<env> --require-approval never`
in that environment's account. Only that environment's app stack is deployed;
the `-github` stack is always deployed by hand.

The deploy role can only be assumed by this repo's workflows running in its own
GitHub environment. Note that the CDK deploy role behind it can create anything
CloudFormation can in that account, so keep the reviewer approval on `prod`.

## Google sign-in setup

Google sign-in uses one Google OAuth client for all environments and a Cognito
hosted domain per environment (`smartvibes-songwriter-<env>`, which must be
unique across AWS). The Google client **secret** is never in the repo or in
GitHub: it is stored in AWS Secrets Manager in each account.

One-time, per account (`dev` and `prod`):

1. In Google Cloud Console (project `smartvibes-songwriter`), the OAuth client
   lists each environment's address as an authorized redirect URI:
   `https://smartvibes-songwriter-<env>.auth.us-east-1.amazoncognito.com/oauth2/idpresponse`.
   The consent screen is in "Testing" mode: only listed test users can sign in
   with Google until the app is published.
2. Store the client secret in that account (type or paste it at the hidden
   prompt; it is not saved in your shell history):
   ```bash
   read -rs GSECRET
   aws secretsmanager create-secret --name smartvibes-songwriter/google-oauth-client-secret \
     --secret-string "$GSECRET" --profile smartvibes-dev   # and smartvibes-prod
   unset GSECRET
   ```
   The stack reads it at deploy time. The deploy fails if the secret does not
   exist in that account.
3. Add the GitHub environment variable `VITE_COGNITO_DOMAIN`
   (`smartvibes-songwriter-<env>.auth.us-east-1.amazoncognito.com`).
4. Deploy. Signing in with Google creates a separate Cognito user from an
   email/password user with the same address; the two are not linked.

## Deploying by hand

Normally the workflow deploys. Deploy by hand only for the **first** deploy of
a new environment (its stack outputs don't exist yet, so the workflow's
variables check would fail), or if GitHub Actions is down.

**First deploy of an environment:** from the repo root, on an up-to-date `main`
with no uncommitted changes:

```bash
scripts/new-env.sh dev     # or prod
```

It picks the profile from the environment name (`smartvibes-dev` or
`smartvibes-prod`), logs you in if needed, removes any local `frontend/dist` (so
another environment's values are not uploaded to this site), shows the diff,
asks before deploying, deploys, and prints the variables to add in GitHub. The
site stays empty until you run the workflow once for that environment.

**Fallback deploy of an existing environment**, if GitHub Actions is down.
Build the frontend first, because the stack uploads `frontend/dist`. The
frontend must be built with that environment's values (`frontend/.env.local`
points at `dev`):

```bash
aws sso login --profile smartvibes-prod
export AWS_PROFILE=smartvibes-prod          # per terminal window
cd frontend && npm run build && cd ..
cd infra && source .venv/bin/activate
cdk diff   SmartvibesSongwriter-prod -c env=prod
cdk deploy SmartvibesSongwriter-prod -c env=prod   # answer y to the IAM prompt
```

Name the stack: a bare `cdk deploy` would also redeploy the `-github` stack.
Use `dev` and `smartvibes-dev` for the dev account.

## Getting the deployed values back

Outputs: `SiteUrl`, `ApiUrl`, `UserPoolId`, `UserPoolClientId`, `TableName`.

```bash
aws cloudformation describe-stacks \
  --stack-name SmartvibesSongwriter-dev \
  --query "Stacks[0].Outputs" \
  --profile smartvibes-dev
```

Use `-prod` and `smartvibes-prod` for prod. Put the dev values in
`frontend/.env.local` (see `frontend/.env.example`):

| Env variable | Stack output |
| ------------ | ------------ |
| `VITE_API_URL` | `ApiUrl` |
| `VITE_COGNITO_USER_POOL_ID` | `UserPoolId` |
| `VITE_COGNITO_CLIENT_ID` | `UserPoolClientId` |

## Quick health check

```bash
curl <ApiUrl>/health          # expect {"status":"ok"}, HTTP 200
curl -i <ApiUrl>/anything     # expect HTTP 401 without a token
```

## One-time setup already done

- AWS account with MFA on the root user; root is not used day to day.
- Monthly budget alarm.
- IAM Identity Center user with `AdministratorAccess`.
- `cdk bootstrap aws://<account-id>/us-east-1` (never needs repeating unless
  the account or region changes).

## What is public and what is secret

Public by design (shipped in the front end): API URL, site URL, user pool ID,
app client ID. Never commit: the Anthropic API key, the Google OAuth client
secret, or any access keys. Those go in AWS Secrets Manager.

## Not done yet

- Frontend files are not uploaded to the site bucket, so `SiteUrl` shows an error.
- Google sign-in on Cognito, and the hosted sign-in domain.
- Secrets Manager secret for the Anthropic API key.
- Automatic deploy from GitHub Actions.

## Tearing down

`cdk destroy` removes the stack but keeps the table and user pool (`RETAIN`);
delete those by hand if you want a full cleanup.
