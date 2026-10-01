# 0003. One AWS account per environment

- Status: Accepted
- Date: 2026-09-30

## Context

The app has a `dev` and a `prod` environment. Both were first deployed into the
single AWS account that had been created for the project. Before any real users
existed, the question came up of whether `prod` should live in its own account.

Two facts forced the decision early:

- A Cognito user pool cannot be moved between AWS accounts. Moving `prod` later,
  after real users had signed up, would mean every user re-registering, or
  building a user-migration process (Cognito can check a password against the
  old pool on first sign-in, but that is extra code to write and test).
- A portfolio project should show how a real team separates environments.

## Options considered

- **One account, several stacks.** Simplest: one bootstrap, one deploy role,
  one place to look. Environments are separated only by resource names, so a
  mistake or a leaked credential in `dev` can reach `prod` data and resources.
- **Separate account for `prod` only.** Protects `prod`, but `dev` workloads
  would stay in the management account, which should hold only the AWS
  Organization and sign-in (IAM Identity Center).
- **Separate account per environment, with a management account that holds no
  workloads.** The usual pattern in real teams. Most setup, but every
  environment is fully isolated.

## Decision

Use one AWS account per environment, all in one AWS Organization:

- the management account holds the Organization and IAM Identity Center only;
- `smartvibes-dev` holds the `dev` environment;
- `smartvibes-prod` holds the `prod` environment.

Each account has its own CDK bootstrap, its own OIDC provider and GitHub deploy
role (trusting only that environment's GitHub workflows), and its own
DynamoDB table, Cognito user pool, API and site. The GitHub environment
variable `AWS_DEPLOY_ROLE_ARN` is set per environment, so one workflow deploys
to the right account. A `test` environment was left out for now; it would get
its own account the same way.

## Consequences

- **Isolation.** A bug, a bad deploy or stolen `dev` credentials cannot touch
  `prod` data. Users and data in the two environments are completely separate.
- **More setup, once.** Creating the accounts, assigning Identity Center access,
  bootstrapping, and deploying the deploy role in each account took a few hours
  and is recorded step by step in `docs/aws-setup-runbook.md`.
- **Easier to make a mistake with the wrong profile.** Every CLI command must
  name the right profile (`smartvibes-dev` or `smartvibes-prod`). The first-deploy
  script derives the profile from the environment name for this reason, and the
  docs say to check the account ID before changing anything.
- **Cost.** AWS accounts are free; the resources in each are billed as before.
- **Future work.** Google sign-in has to be configured in each environment's
  user pool. A `test` environment needs its own new account.
- **A step toward least privilege.** Day-to-day work still uses
  `AdministratorAccess`. A later improvement would be a read-only role for
  `prod` and developer-level roles elsewhere.
