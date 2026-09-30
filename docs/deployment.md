# Deployment notes

How the AWS side of this project is set up and operated. No real IDs or
secrets belong in this file; values for the deployed stack live in
`frontend/.env.local` (git-ignored) and can always be re-read from AWS.

## Where things live

| Thing | Value |
| ----- | ----- |
| AWS region | `us-east-1` |
| CDK stack | `SmartvibesSongwriter-dev` |
| AWS CLI profile | `smartvibes-dev` (IAM Identity Center / SSO login) |
| Resource naming | `smartvibes-songwriter-<env>-<resource>` |
| Stateful resources | DynamoDB table and Cognito user pool are `RETAIN` (survive stack deletion) |

## Automatic deploy (GitHub Actions)

`.github/workflows/deploy.yml` deploys the app stack when something is merged
to `main`. It signs in to AWS with a short-lived OIDC (OpenID Connect) token,
so no AWS keys are stored in GitHub. The job runs in the GitHub environment
`production`, which waits for a reviewer to approve each deploy.

### One-time setup

1. **Deploy the GitHub access stack** (creates the OIDC provider and the deploy
   role in AWS; run by hand, from `infra/` with the venv active and your AWS
   login):
   ```bash
   cdk deploy SmartvibesSongwriter-github
   ```
   Copy the `DeployRoleArn` output.
2. **Create the environment** in GitHub: repo Settings > Environments > New
   environment, named `production`. Under "Required reviewers", add yourself.
3. **Add variables to that environment** (Settings > Environments > production
   > Environment variables). None of these are secret:

   | Variable | Value |
   | -------- | ----- |
   | `AWS_DEPLOY_ROLE_ARN` | `DeployRoleArn` from step 1 |
   | `VITE_API_URL` | `ApiUrl` stack output |
   | `VITE_COGNITO_USER_POOL_ID` | `UserPoolId` stack output |
   | `VITE_COGNITO_CLIENT_ID` | `UserPoolClientId` stack output |
   | `VITE_COGNITO_REGION` | `us-east-1` |

### What happens on each merge

The workflow waits for your approval, builds the frontend, then runs
`cdk deploy SmartvibesSongwriter-dev --require-approval never`. Only the app
stack is deployed; `SmartvibesSongwriter-github` is always deployed by hand.

The role can only be assumed by this repo's workflows running in the
`production` environment. Note that the CDK deploy role behind it can create
anything CloudFormation can, so keep reviewer approval on.

## Deploying with the script (temporary)

> **Fallback.** `scripts/deploy.sh` was a stopgap until the GitHub Actions
> deploy above was set up. Once that works, remove this section or keep it
> only as a break-glass option.

Before deploying, merge your branch and update local `main`
(`git checkout main && git pull`) so you deploy what is on `main`.

```bash
scripts/deploy.sh diff   # build the frontend, then preview only; changes nothing
scripts/deploy.sh        # build the frontend, then cdk deploy
```

The script uses the `smartvibes-dev` profile, logs in through SSO if the
session has expired, stops if `frontend/.env.local` is missing, builds
`frontend/`, then runs `cdk` from `infra/` with its virtual environment on.
`cdk deploy` still asks you to approve IAM (permission) changes; answer `y`
after reading them.

## Daily workflow (manual steps)

What the script does, step by step. The frontend must be built first, because
the stack uploads `frontend/dist` to the site bucket.

```bash
# 1. Log in (SSO sessions last 8 hours)
aws sso login --profile smartvibes-dev

# 2. Tell this terminal which profile to use (repeat in every new terminal window)
export AWS_PROFILE=smartvibes-dev

# 3. Build the frontend
cd frontend && npm run build && cd ..

# 4. From infra/, with the venv active
cd infra && source .venv/bin/activate
cdk diff      # preview changes, changes nothing
cdk deploy    # apply; answer y to the IAM approval prompt
```

## Getting the deployed values back

Outputs: `SiteUrl`, `ApiUrl`, `UserPoolId`, `UserPoolClientId`, `TableName`.

```bash
aws cloudformation describe-stacks \
  --stack-name SmartvibesSongwriter-dev \
  --query "Stacks[0].Outputs" \
  --profile smartvibes-dev
```

Put them in `frontend/.env.local` (see `frontend/.env.example`):

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
