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

## Daily workflow

```bash
# 1. Log in (SSO sessions last 8 hours)
aws sso login --profile smartvibes-dev

# 2. Tell this terminal which profile to use (repeat in every new terminal window)
export AWS_PROFILE=smartvibes-dev

# 3. From infra/, with the venv active
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
