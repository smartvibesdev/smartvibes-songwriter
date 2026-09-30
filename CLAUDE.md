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

- Region `us-east-1`. Use the SSO profile `smartvibes-dev` (`export AWS_PROFILE=smartvibes-dev`; log in with `aws sso login --profile smartvibes-dev`).
- CDK stack `SmartvibesSongwriter-dev`. Resource names follow `smartvibes-songwriter-<env>-<resource>`. The DynamoDB table and Cognito user pool use `RETAIN`.
- Real Cognito and API values live in the git-ignored `frontend/.env.local`. Never commit secrets, API keys, or `.env.local`.
- Every AI call must go through the token-budget checkpoint described in the plan. No route may call the Anthropic API directly.
