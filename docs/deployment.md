# Deployment notes

How the AWS side of this project is set up and operated. No real IDs or
secrets belong in this file; values for the deployed stack live in
`frontend/.env.local` (git-ignored) and can always be re-read from AWS.

## Where things live

| Thing              | Value                                                                      |
| ------------------ | -------------------------------------------------------------------------- |
| AWS region         | `us-east-1`                                                                |
| CDK stack          | `SmartvibesSongwriter-dev`                                                 |
| AWS CLI profile    | `smartvibes-dev` (IAM Identity Center / SSO login)                         |
| Resource naming    | `smartvibes-songwriter-<env>-<resource>`                                   |
| Stateful resources | DynamoDB table and Cognito user pool are `RETAIN` (survive stack deletion) |

## Automatic deploy (GitHub Actions)

There are three environments: `dev`, `test` and `prod`. Each one is a separate
CDK stack in AWS (`SmartvibesSongwriter-dev`, `-test`, `-prod`) with its own
table, user pool, API and site.

`.github/workflows/deploy.yml` is one workflow that deploys whichever
environment it is given:

- **Merging to `main` deploys `dev`.**
- **To deploy another environment:** GitHub repo > Actions > Deploy > Run
  workflow, then pick `dev`, `test` or `prod`.

It signs in to AWS with a short-lived OIDC (OpenID Connect) token, so no AWS
keys are stored in GitHub. Each deploy runs in the GitHub _environment_ of the
same name. The environment holds that environment's variables and its approval
rule (for example, you must approve before anything deploys to `prod`).

### One-time setup: the AWS deploy role (once for the whole account)

Run by hand, from `infra/` with the venv active and your AWS login:

```bash
cdk deploy SmartvibesSongwriter-github
```

This creates the OIDC provider and one deploy role that workflows running in
the `dev`, `test` or `prod` environment of this repo may use. Copy the
`DeployRoleArn` output; you need it for every environment below.

### One-time setup: each environment (repeat for dev, test, prod)

1. **Create the environment** in GitHub: repo Settings > Environments > New
   environment, named `dev` (or `test`, `prod`). Under "Required reviewers",
   add yourself. Do this before the first deploy; if GitHub creates the
   environment on its own, it has no reviewer and would deploy without asking.
2. **Add variables to that environment** (Settings > Environments > the
   environment > Environment variables). None of these are secret, and the
   names are the same in every environment while the values differ:

   | Variable                    | Value                                        |
   | --------------------------- | -------------------------------------------- |
   | `AWS_DEPLOY_ROLE_ARN`       | `DeployRoleArn` from the step above          |
   | `VITE_API_URL`              | that environment's `ApiUrl` stack output     |
   | `VITE_COGNITO_USER_POOL_ID` | that environment's `UserPoolId` output       |
   | `VITE_COGNITO_CLIENT_ID`    | that environment's `UserPoolClientId` output |
   | `VITE_COGNITO_REGION`       | `us-east-1`                                  |

   For a brand-new environment, its stack outputs don't exist until the stack
   has been deployed once. Deploy it the first time by hand (see "Deploying by
   hand" below), copy the outputs into the variables, then use the workflow
   from then on.

### What happens on each deploy

The workflow waits for the environment's approval, checks that the variables
are set, builds the frontend, then runs
`cdk deploy SmartvibesSongwriter-<env> -c env=<env> --require-approval never`.
Only that environment's app stack is deployed; `SmartvibesSongwriter-github` is
always deployed by hand.

The deploy role can only be assumed by this repo's workflows running in the
`dev`, `test` or `prod` environment. Note that the CDK deploy role behind it
can create anything CloudFormation can, so keep reviewer approval on,
especially for `prod`.

## Deploying by hand

`scripts/new-env.sh <env>` runs the first-deploy steps for a new environment.

Normally the workflow above deploys. Deploy by hand only for the **first**
deploy of a new environment (its stack outputs don't exist yet, so the
workflow's variables check would fail), or if GitHub Actions is down.

The frontend must be built first, because the stack uploads `frontend/dist` to
the site bucket. For a brand-new environment, skip the build and remove any old
one (`rm -rf frontend/dist`) so another environment's values are not uploaded
to the wrong site.

```bash
# 1. Log in (SSO sessions last 8 hours)
aws sso login --profile smartvibes-dev

# 2. Tell this terminal which profile to use (repeat in every new terminal window)
export AWS_PROFILE=smartvibes-dev

# 3. Build the frontend (skip for a brand-new environment; see above)
cd frontend && npm run build && cd ..

# 4. From infra/, with the venv active. Name the stack: a bare `cdk deploy`
#    would also redeploy the GitHub access stack.
cd infra && source .venv/bin/activate
cdk diff   SmartvibesSongwriter-dev -c env=dev   # preview, changes nothing
cdk deploy SmartvibesSongwriter-dev -c env=dev   # apply; answer y to the IAM prompt
```

Use the environment's name in place of `dev` for `test` or `prod`. Merge your
branch and update local `main` first, so you deploy what is on `main`.

## Getting the deployed values back

Outputs: `SiteUrl`, `ApiUrl`, `UserPoolId`, `UserPoolClientId`, `TableName`.

```bash
aws cloudformation describe-stacks \
  --stack-name SmartvibesSongwriter-dev \
  --query "Stacks[0].Outputs" \
  --profile smartvibes-dev
```

Put them in `frontend/.env.local` (see `frontend/.env.example`):

| Env variable                | Stack output       |
| --------------------------- | ------------------ |
| `VITE_API_URL`              | `ApiUrl`           |
| `VITE_COGNITO_USER_POOL_ID` | `UserPoolId`       |
| `VITE_COGNITO_CLIENT_ID`    | `UserPoolClientId` |

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
