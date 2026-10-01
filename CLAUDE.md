# CLAUDE.md

Instructions for Claude Code when working in this repository.

## Working agreement

- **Never commit, push, merge, open a PR, or deploy unless the user explicitly asks in that message.** Make edits, leave them uncommitted so they can be reviewed and tested in VS Code's Source Control panel, and say which files changed. One approval covers only that one action.
- **This includes `cdk deploy` and any other command that creates, changes, or deletes AWS resources.** Read-only checks (for example `cdk diff`, `cdk synth`, `aws sts get-caller-identity`) are fine.
- **Ask before making AWS assumptions** (region, account, naming, permissions).
- **Define acronyms the first time they appear** in a reply (for example, "ADR (Architecture Decision Record)"). The user is an experienced developer who is new to Python tooling and AWS, so explain what commands do and why, and give exact commands.
- Write complete, grammatical sentences. Say plainly what was and wasn't verified; don't claim something works if it was only built or synthesized, not run.

## Git

- Commit as the `smartvibesdev` identity. The author email is set in this repo's `.git/config` (`165607164+smartvibesdev@users.noreply.github.com`). Do not change it, and do not use `jk@jeffknutson.net`.
- Work on a branch, never directly on `main`. Branch names are short and descriptive.
- Commit messages: a short summary line, and a short body when useful. End with the `Co-Authored-By` line specified by the session's attribution instructions.

## Project

Songwriting companion app. See `docs/sv-songwriter-project-plan.md` for the plan and `docs/adr/` for decisions.

| Folder      | What                                          | Tooling                                |
| ----------- | --------------------------------------------- | -------------------------------------- |
| `frontend/` | React + TypeScript (Vite)                     | `npm`; lint with `oxlint`              |
| `backend/`  | FastAPI on AWS Lambda (Mangum)                | Python 3.12, `.venv`, `pytest`, `ruff` |
| `infra/`    | AWS CDK (Python)                              | `.venv`; `cdk` needs it active         |
| `docs/`     | Plan, ADRs, `development.md`, `deployment.md` | Markdown                               |

- Python commands (`pytest`, `ruff`, `uvicorn`, `cdk`) need the folder's virtual environment: `source .venv/bin/activate`. Each Python folder has its own.
- Checks that CI runs: backend `ruff check .`, `ruff format --check .`, `pytest`; frontend `npm run lint`, `npm run build`; infra `python app.py` (synth).
- See `docs/development.md` for setup and `docs/deployment.md` for AWS operations.

## AWS

- Region `us-east-1`. Three AWS accounts in one Organization, one SSO session, three CLI profiles: `smartvibes-mgmt` (organization and Identity Center only, no app resources), `smartvibes-dev` (the `dev` environment) and `smartvibes-prod` (the `prod` environment). Log in with `aws sso login --profile smartvibes-dev`. Check which account a profile points at with `aws sts get-caller-identity --profile <name>` before changing anything.
- One CDK stack per environment, in its own account: `SmartvibesSongwriter-dev`, `SmartvibesSongwriter-prod`. Each account also has a `SmartvibesSongwriter-github` stack (GitHub deploy role; deploy with `-c env=<env>`). Resource names follow `smartvibes-songwriter-<env>-<resource>`. The DynamoDB table and Cognito user pool use `RETAIN`.
- Deploys normally run through the GitHub Deploy workflow. A merge to `main` deploys `dev` automatically with no approval; `prod` is run by hand from the Actions tab and needs the owner's approval. Only `main` deploys; there is no `develop` branch and feature branches do not deploy (ADR 0006). Use `scripts/new-env.sh <env>` only for the first deploy of an environment. Never deploy to the wrong account: always pass the matching `--profile`.
- Real Cognito and API values live in the git-ignored `frontend/.env.local` (points at `dev`). Never commit secrets, API keys, or `.env.local`.
- Every AI call must go through the token-budget checkpoint described in the plan. No route may call the Anthropic API directly.
