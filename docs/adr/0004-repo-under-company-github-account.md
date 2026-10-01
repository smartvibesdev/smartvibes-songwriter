# 0004. Host the repository under the company GitHub account

- Status: Accepted
- Date: 2026-09-30

## Context

The project plan listed "personal GitHub vs. company GitHub" as an open
decision to settle in Week 1. The author owns a company, Smart Vibes, and is
its only employee. The company already has a GitHub account, `smartvibesdev`.

## Options considered

- **Personal GitHub account.** Ties the project to the author's own profile and
  history. Mixes this work with unrelated personal repositories.
- **Company GitHub account (`smartvibesdev`).** Keeps the project with the
  company that owns the work, alongside the company's AWS accounts and domain.
  The author still builds a public portfolio, under the company name.

## Decision

Host the repository at `smartvibesdev/smartvibes-songwriter`. Commits in this
repo are authored as the `smartvibesdev` GitHub identity (its noreply email,
set in the repo's local git config), not the author's personal address.

## Consequences

- The project, its AWS accounts (see ADR 0003) and its GitHub deploy
  permissions all belong to the company.
- GitHub attributes commits by author email, so the repo-local git setting
  matters: a commit made with a personal email shows up under the personal
  account. A few early commits on `main` already carry the personal email and
  were left as they are.
- The deploy role trusts this repository by its permanent GitHub IDs, so moving
  or renaming the repository later means updating that trust rule and
  redeploying the `-github` stack in each AWS account.
- The `LICENSE` file currently names the author personally as copyright holder.
  Whether it should name the company instead is a separate question.
