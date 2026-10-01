# AWS and deployment setup runbook

How this project's AWS account, tooling, sign-in and automatic deploys were set
up, in the order they were done, including what went wrong and how it was
fixed. Written so the setup can be repeated (or debugged) without starting over.

Day-to-day commands live in [deployment.md](deployment.md) and
[development.md](development.md). This file is the long-form history and
troubleshooting guide.

No account IDs, keys or tokens are recorded here. `<account-id>` means your
12-digit AWS account number.

## Glossary

| Term | Meaning |
| ---- | ------- |
| **ADR** | Architecture Decision Record: a one-page file in `docs/adr/` recording one technical decision, the options considered, what was chosen and why. |
| **AWS** | Amazon Web Services. |
| **CDK** | AWS Cloud Development Kit: defines AWS resources as Python code (`infra/`). |
| **CI** | Continuous integration: the automatic checks GitHub runs on every pull request (`.github/workflows/ci.yml`). |
| **CLI** | Command-line interface; here the `aws` and `cdk` commands. |
| **CloudFormation** | AWS's built-in service for creating and managing resources from a template. CDK generates the template, CloudFormation builds it. Its console page is the best overview of what this project created. |
| **CORS** | Cross-origin resource sharing: the browser rule controlling which websites may call an API. |
| **IAM** | Identity and Access Management: AWS users, roles and permissions. |
| **MFA** | Multi-factor authentication: a second login step from an authenticator app. |
| **OIDC** | OpenID Connect: lets GitHub prove its identity to AWS with a short-lived token, so no AWS keys are stored in GitHub. |
| **PR** | Pull request. |
| **Stack** | A group of AWS resources created, updated and deleted together as one unit by CloudFormation. This project has one stack per environment (`SmartvibesSongwriter-dev`, `SmartvibesSongwriter-prod`), plus `SmartvibesSongwriter-github` (the GitHub deploy role) and `CDKToolkit` (the bootstrap). |
| **SSO** | Single sign-on; here AWS IAM Identity Center. |

## Where things stand

- **Region:** `us-east-1`. **Account:** one AWS account, named "Smart Vibes".
- **Environments:** `dev` (stack `SmartvibesSongwriter-dev`) and `prod` (stack
  `SmartvibesSongwriter-prod`) both exist, in the same account and region.
  `test` is not created yet; see "Adding an environment".
- **Deploys:** merging to `main` starts the Deploy workflow for `dev`, which
  waits for your approval in GitHub, then deploys.
- **Sign-in:** email and password through Amazon Cognito. Google sign-in is not
  done yet.
- **Live check:** `GET <ApiUrl>/health` returns `{"status":"ok"}`.

## 1. AWS account

1. Sign up at aws.amazon.com. The email used becomes the **root user**.
2. Choose the **Paid** account plan, not Free. Both give the same starter
   credits. The Free plan closes the account after 6 months and limits which
   services can be used. "Paid" only charges once credits are used up.
3. Payment method: choose **credit or debit card**, not bank account. A card
   allows disputes and keeps AWS away from your bank account. AWS places a
   temporary $1 verification hold.
4. Support plan: **Basic (free)**.
5. The console may default to another region. Switch it to **N. Virginia
   (`us-east-1`)** in the top-right selector.

## 2. Protect the root user

1. **MFA on root:** account name (top right) > Security credentials >
   Multi-factor authentication > Assign MFA device > Authenticator app. Scan
   the QR code, enter two consecutive codes.
2. **Budget alarm:** search "Budgets" > Create budget > Use a template
   (simplified) > Monthly cost budget > name `monthly-10-usd`, amount `10`,
   your email > Create.
3. Stop using root for daily work once the next step is done.

## 3. Day-to-day login: IAM Identity Center (SSO)

Used instead of long-lived access keys.

1. Search "IAM Identity Center" > **Enable**. Choose the **organization
   instance** (the page titled "Enable IAM Identity Center with AWS
   Organizations").
2. Instance configuration: choose **Single-Region instance**. Multi-Region
   replicates to a second region and adds KMS key charges you don't need.
3. **Users > Add user:** a username (this project uses `jeff`; never a
   "root-" name), your email and name. Skip the optional groups step. An
   invitation email is sent and its link lasts 7 days.
4. **Permission sets > Create permission set:** Predefined >
   **AdministratorAccess**. Then edit it and set **Session duration to 8
   hours** (the default is 1 hour).
5. **AWS accounts:** tick the account > Assign users or groups > the user >
   the `AdministratorAccess` permission set > Submit. This is easy to miss. The
   permission set page must show "AWS accounts (1)", not 0, or the CLI later
   reports "No AWS accounts are available to you".
6. Accept the invitation email, set a password and register MFA for this user.
7. Copy the **AWS access portal URL** from Identity Center > Settings. It looks
   like `https://d-xxxxxxxxxx.awsapps.com/start`. **The `d-xxxxxxxxxx.` part
   is required.** The bare `awsapps.com/start` shows an "AccessDenied" XML
   error. Bookmark the full address: it is how you sign in to the AWS console
   (see "Seeing the environments in the AWS console"). You can also find it with
   `grep sso_start_url ~/.aws/config`.

## 4. Local tooling

```bash
brew install awscli aws-cdk
aws --version    # 2.3x or newer, native arm64 build on Apple silicon
cdk --version
```

An older AWS CLI installed by AWS's `.pkg` installer was removed first
(`sudo rm /usr/local/bin/aws /usr/local/bin/aws_completer && sudo rm -rf
/usr/local/aws-cli`) so two copies would not compete on the PATH.

Connect the CLI to SSO (in a normal terminal):

```bash
aws configure sso
```

| Prompt | Answer |
| ------ | ------ |
| SSO session name | `smartvibes` |
| SSO start URL | the access portal URL from step 3 |
| SSO region | `us-east-1` |
| Registration scopes | Enter (default) |
| (browser opens) | sign in, click **Allow access** |
| Account / role | your account / `AdministratorAccess` |
| Default region / output | `us-east-1` / `json` |
| Profile name | `smartvibes-dev` |

The CLI may offer to configure "AWS skills and the AWS MCP server" for AI
coding tools. This project answered **n**; it is unrelated to login.

Verify, then use the profile:

```bash
aws sts get-caller-identity --profile smartvibes-dev   # shows account and your role
export AWS_PROFILE=smartvibes-dev                       # per terminal window
aws sso login --profile smartvibes-dev                  # after the 8-hour session expires
```

Tip: `aws configure set cli_pager ""` stops the `(END)` pager on long output.
Press `q` to leave the pager if it appears.

## 5. First deploy with CDK

1. **Bootstrap once per account and region.** Creates a storage bucket and
   roles that CDK uses for every later deploy:
   ```bash
   export AWS_PROFILE=smartvibes-dev
   cdk bootstrap aws://<account-id>/us-east-1
   ```
   The yellow note about the default `AdministratorAccess` execution policy is
   expected.
2. **Preview, then deploy** from `infra/` (needs its virtual environment, see
   below):
   ```bash
   cd infra && source .venv/bin/activate
   cdk diff   SmartvibesSongwriter-dev   # changes nothing
   cdk deploy SmartvibesSongwriter-dev   # answer y to the IAM changes prompt
   ```
   The first deploy took about 4 minutes, mostly CloudFront.
3. **The outputs** (`ApiUrl`, `SiteUrl`, `UserPoolId`, `UserPoolClientId`,
   `TableName`) are what the frontend needs. Re-read them any time:
   ```bash
   aws cloudformation describe-stacks --stack-name SmartvibesSongwriter-dev \
     --query "Stacks[0].Outputs" --profile smartvibes-dev
   ```
   Put the frontend ones in `frontend/.env.local` (git-ignored). See
   `frontend/.env.example`.
4. **Smoke test:**
   ```bash
   curl <ApiUrl>/health          # {"status":"ok"}, HTTP 200
   curl -i <ApiUrl>/anything     # HTTP 401 without a token
   ```

### What a virtual environment is, and when you need it

`(.venv)` at the start of the prompt means a Python virtual environment is
active: a private folder of libraries for one project. Turn one on with
`source .venv/bin/activate` (from `backend/` or `infra/`) and off with
`deactivate`. Python tools (`pytest`, `ruff`, `uvicorn`, and every `cdk`
command, because the stack is Python) need the folder's environment on. `npm`
commands do not. "command not found: uvicorn" or `ModuleNotFoundError` means it
is off. Each Python folder has its own environment. See
[development.md](development.md).

## 6. Sign-in and the `/me` test

Email sign-up, email verification code and sign-in use the Cognito user pool
directly from the browser (`amazon-cognito-identity-js`). `GET /me` returns the
signed-in user's ID and email, read from the token that API Gateway has already
verified. Test by opening the `SiteUrl`, signing up, confirming the emailed
code, signing in and clicking **Call /me**. You should see `200` and your user
ID and email.

Google sign-in is not set up yet. It needs a Google OAuth client and a
Cognito hosted sign-in domain.

## 7. Anthropic account

- The account uses **prepaid credits with auto-reload off**. Spending cannot
  pass the balance, because calls fail when the credits run out. This is the
  hard ceiling. Leave auto-reload off.
- Spend-limit page: Console > Manage > Spend limits. The default workspace's
  limit is managed under organization settings. It is optional because of the
  prepaid cap.
- A dedicated API key named `smartvibes-songwriter-dev` was created for this
  project, stored in a password manager. **Never commit it or paste it in a
  chat.** It is first used in Week 3 (stored in AWS Secrets Manager).
- Anthropic offers identity federation (no stored key). The plan uses a normal
  key for now; moving to federation is a possible later ADR.

## 8. Git and GitHub conventions

- Remote: `smartvibesdev/smartvibes-songwriter`. Commits in this repo use the
  author email `<id>+smartvibesdev@users.noreply.github.com`, set **in the
  repo's `.git/config`**, not globally. GitHub attributes commits by author
  email, not by which SSH key pushed. Set it again after a fresh clone:
  `git config user.email "<that address>"`.
- Work on a branch; merge through a pull request (CI must pass).
- **CI** (`ci.yml`) runs on every PR: backend ruff and pytest, frontend oxlint
  and build, infra CDK synth. None of it touches AWS.
- Setting "Automatically delete head branches" (repo Settings > General >
  Pull Requests) removes merged remote branches. Delete local ones with
  `git branch -d <name>`.

## 9. Automatic deploy (GitHub Actions to AWS)

`deploy.yml` deploys one environment per run. A merge to `main` deploys `dev`;
other environments are deployed by **Actions > Deploy > Run workflow** and
picking the environment. See [deployment.md](deployment.md) for the variable
table.

How it works: GitHub gives the job a short-lived OIDC token. AWS has an OIDC
provider for GitHub and one IAM role
(`smartvibes-songwriter-github-deploy`) that trusts tokens from this repo's
`dev`, `test` and `prod` GitHub environments. The role only assumes CDK's own
bootstrap roles, which do the real work.

One-time setup, in this order (**all before the first merge that adds the
workflow**, because the merge itself starts a deploy):

1. `cdk deploy SmartvibesSongwriter-github` from `infra/`. Copy the
   `DeployRoleArn` output.
2. GitHub > repo Settings > Environments > New environment, named exactly
   `dev`. Tick **Required reviewers**, add yourself and **click Save protection
   rules**. Leave "Prevent self-review" **off**; if it is on, you cannot
   approve a deploy you started. If the environment is created automatically
   instead, it has no reviewer and deploys without asking.
3. On that environment add five **environment variables** (not secrets; none
   are sensitive): `AWS_DEPLOY_ROLE_ARN`, `VITE_API_URL`,
   `VITE_COGNITO_USER_POOL_ID`, `VITE_COGNITO_CLIENT_ID`,
   `VITE_COGNITO_REGION`.
4. Merge. The run waits at "Waiting for review": open it, **Review
   deployments**, tick the environment, **Approve and deploy**.

## Seeing the environments in the AWS console

`dev` and `prod` are in the same AWS account and region (`us-east-1`), so one
sign-in shows both.

1. Open your full access portal address (`https://d-xxxxxxxxxx.awsapps.com/start`),
   sign in as your Identity Center user, click the account, then
   **Management console** next to `AdministratorAccess`. Do not use the root
   login for this.
2. Check the region selector (top right) says **N. Virginia (us-east-1)**.
   Resources only appear in the region where they were created.
3. Search for **CloudFormation**. Each environment is one stack. Click a stack,
   then **Resources** for everything it created (each row links to that
   resource's console page) and **Outputs** for its URLs and IDs.
4. Individual services also list them, with the environment in the name:
   DynamoDB tables (`smartvibes-songwriter-<env>-table`), Lambda functions
   (`...-<env>-api`), Cognito user pools, API Gateway APIs and CloudFront
   distributions. S3 site buckets have generated names; use the stack's
   Resources tab to find them.

## 10. Problems hit, and the fixes

| Symptom | Cause | Fix |
| ------- | ----- | --- |
| `No AWS accounts are available to you` from `aws configure sso` | The permission set was created but never assigned to the account | Identity Center > AWS accounts > Assign users or groups |
| `The config profile (smartvibes-dev) could not be found` | The earlier SSO setup had not finished, so no profile was written | Finish `aws configure sso` |
| `zsh: command not found: uvicorn` (or `pytest`, `ruff`) | Virtual environment not active | `source .venv/bin/activate` in that folder |
| Opening `awsapps.com/start` shows an XML `AccessDenied` error | The address is missing the directory ID | Use the full `https://d-xxxxxxxxxx.awsapps.com/start` from Identity Center > Settings |
| `ReferenceError: global is not defined`, blank page in the browser | `amazon-cognito-identity-js` expects Node's `global` | `define: { global: 'globalThis' }` in `frontend/vite.config.ts` |
| Browser CORS error calling `/me`; preflight (OPTIONS) returns 401 | A catch-all route with a token check also caught the browser's OPTIONS preflight | Explicit routes (`/health` public, `/{proxy+}` protected) and no `$default` route, so API Gateway answers preflights itself |
| Clicked `localhost` links open inside VS Code instead of Chrome | VS Code setting "Workbench > Browser: Open Localhost Links" | Untick it in Settings |
| Deploy run: `Could not assume role with OIDC: Not authorized to perform sts:AssumeRoleWithWebIdentity` | New GitHub repos name themselves in OIDC tokens with permanent IDs (`repo:owner@<id>/name@<id>`), not the plain `repo:owner/name` the role trusted | Trust the ID-based name. Get it with `gh api repos/OWNER/REPO/actions/oidc/customization/sub` (field `sub_claim_prefix`), set it in `infra/app.py`, redeploy the `-github` stack by hand |
| Commits show up under a personal GitHub account | Git used the global author email | Set the repo-local email (section 8) |
| `gh api .../variables` returns 403 | The `gh` CLI login lacks repo admin | Read variables in the GitHub web UI |
| `cdk` prints a "not tested with node v26" box | Homebrew installed Node 26; CDK's Python layer supports 20, 22 and 24 | Harmless. Switch to Node 24 if it ever breaks |
| `git pull` fails with "Permission denied (publickey)" from a sandboxed tool | SSH key not available in that context | Run `git pull` in your own terminal |

## Adding an environment (test or prod)

`dev` and `prod` exist (`prod` was created on 2026-09-30 with
`scripts/new-env.sh prod`, then deployed again through the workflow). `test` is
not created yet. The stack code supports any of them: the environment name sets the stack name and every resource name, so
`-c env=prod` produces `SmartvibesSongwriter-prod` with its own table, user
pool, API and site. They share the one AWS account for now (separate accounts
would be stricter for prod but need their own bootstrap and SSO assignment).

Checklist (written for `prod`; the same steps apply to `test`):

0. **Shortcut for step 1 and the values in step 2:** from the repo root on an
   up-to-date `main`, run `scripts/new-env.sh prod`. It logs you in if needed,
   removes `frontend/dist`, shows the diff, asks before deploying, deploys, and
   prints the variables to add in GitHub. The manual steps below are what it does.
1. **Deploy the stack by hand the first time.** Its outputs do not exist yet,
   so the workflow's variables check would fail. Build no frontend first
   (`rm -rf frontend/dist`) so `dev`'s values are not uploaded to the wrong
   site. From `infra/` with the environment on:
   `cdk deploy SmartvibesSongwriter-prod -c env=prod`. The workflow cannot do
   this first deploy, because its variables do not exist yet.
2. Copy the new `ApiUrl`, `UserPoolId` and `UserPoolClientId` outputs.
3. In GitHub, create the `prod` environment with yourself as a required
   reviewer (save it) and add the same five variable names with prod's values
   and the same `AWS_DEPLOY_ROLE_ARN`.
4. Run **Actions > Deploy > Run workflow**, choose `prod`, approve. This
   builds the frontend with prod's values and uploads it.
5. Sign up a test user on the prod `SiteUrl` and click **Call /me**.
6. Repeat for `test` if wanted.

Adding `prod` this way worked as written: the first deploy by script, then the
five variables on the GitHub environment, then a manual workflow run.

## Next

- Google sign-in (needs a Google OAuth client; see the plan).
- ADR for repo location (is `smartvibesdev` personal or company GitHub).
- Week 2: songs and fragments.
