# 0006. Deployment flow: merge deploys dev, prod is manual

- Status: Accepted
- Date: 2026-10-01

## Context

Deploys run through one GitHub Actions workflow that takes an environment name.
At first, every deploy, including `dev`, waited for a manual approval in GitHub.
That meant an extra click after every merge, and a stalled "waiting" run once
left `dev` behind `main` without anyone noticing.

This is a solo portfolio project. The goal is to show sound, simple practice
with AWS and AI tooling, not elaborate release engineering.

## Options considered

- **Approval on every environment** (the starting point). Safe, but an extra
  step for each `dev` deploy.
- **Merge to `main` deploys `dev` with no approval; `prod` is a manual run
  that needs approval.** One click saved per change; `prod` stays protected.
- **The same, but `prod` is chained after `dev` in one run and waits for an
  approval at the end.** One fewer trip to the Actions tab, but every merge
  leaves a pending `prod` approval behind.
- **A `develop` branch (deploys `dev`) plus `main` (deploys `prod`).** A common
  pattern for teams with scheduled releases. For one developer it means two
  long-lived branches and a second pull request for every release.
- **Letting `feature-*` branches deploy to `dev`.** Possible with an
  environment branch rule, but there is only one `dev`, so branches would
  overwrite each other and `dev` would stop mirroring `main`.

## Decision

- **One long-lived branch, `main`.** Changes arrive through pull requests from
  short-lived branches, and CI must pass first.
- **A merge to `main` deploys `dev` automatically, with no approval.** The `dev`
  GitHub environment has no required reviewer, and only `main` may deploy to it.
- **`prod` is deployed by hand:** Actions > Deploy > Run workflow > `prod`. The
  `prod` GitHub environment requires an approval from the owner, and only `main`
  may deploy to it.
- No `develop` branch, and no deploys from `feature-*` branches for now.

## Consequences

- `dev` always reflects `main` shortly after a merge. A merge that changes only
  docs (`docs/**`, `.md` files, the CI workflow file) does not start a deploy;
  the Deploy workflow can still be run by hand for any environment.
- `prod` only changes when the owner chooses and approves, and always from
  `main`.
- Nothing on `dev` is reviewed before it deploys, so a bad merge reaches `dev`
  immediately. That is acceptable for a development environment, and CI runs on
  every pull request first.
- Revisit if there are more contributors: a `develop` branch, per-branch
  previews, or chaining `prod` after `dev` in one run could each be added then.
  A `test` environment would be a further stage with its own approval rule.
