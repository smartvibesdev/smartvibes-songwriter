# CLAUDE.md

Instructions for Claude Code when working in this repository.

## Working agreement

- **Commit finished work on a branch, and nothing more.** Start each task on a short, descriptive branch created from `main`. Run `git branch --show-current` before every commit and stop if it says `main`. When the task passes its checks, commit it; never commit unfinished or failing work, and never commit to `main`. Then report the commit hash and the exact push command.
- **Never push, merge, open a PR, or deploy unless the user explicitly asks in that message.** One approval covers only that one action.
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
- Checks that CI runs: backend `ruff check .`, `ruff format --check .`, `pytest`; frontend `npm run lint`, `npm run format:check`, `npm run build`; infra `python app.py` (synth).
- See `docs/development.md` for setup and `docs/deployment.md` for AWS operations.

## TypeScript style (`frontend/`)

Formatting is automatic: Prettier with no semicolons, single quotes and a 120-character line width, otherwise default settings (so trailing commas). Run `npm run format` to fix and `npm run format:check` to verify; both cover `src/`. The structure rules below are checked by `oxlint` where it can (`curly`, `no-negated-condition`, `eqeqeq`) and by review otherwise.

1. **No single-line `if` statements.** The body always goes on its own line, inside braces.
2. **Always use braces** on `if`, `else`, `for`, `while`, `do` and similar. Never `if (x) return y` and never `for (...) doIt()`.
3. **Put whitespace between lines of logic.** Group related statements, then leave a blank line before the next group. Every `if`/`for`/`while`/`try`/`switch` block gets a blank line before and after it (unless it is the first or last thing in its block). A `return` after other statements gets a blank line before it. Declarations are separated from the logic that uses them. Do not write dense runs of statements or deeply packed one-liners; give a long expression a named variable.
4. **Use positive logic.** Test for the thing you want, not for its opposite.
   - Do not use `!`, `!==` or `!=` in conditions when a positive form exists. Write `if (response.ok)`, not `if (!response.ok)`; use `Boolean(x)` where you need a boolean from a value.
   - Checking for absence with `=== null` or `=== undefined` is positive and fine, for example a guard such as `if (token === null) { throw ... }`.
   - The one accepted exception is dropping an item from a collection, which has no positive form: keep that `!==` inside a small named helper in `src/lists.ts` (`removeById`, `toggleItem`) and call the helper.
   - Never write `if (!a) { ... } else { ... }` or `a !== b ? x : y`. Swap the branches.
   - Put the main case inside the positive `if` and the failure or fallback after it.
   - If a condition is hard to read, name it: `const isFresh = expiresAt - now > 60_000`.

Also: keep functions small and single-purpose (split anything that parses, branches and formats in one body); avoid nested ternaries (use a lookup object or `if` blocks); give variables full names (`response`, not `r`).

## AWS

- Region `us-east-1`. Three AWS accounts in one Organization, one SSO session, three CLI profiles: `smartvibes-mgmt` (organization and Identity Center only, no app resources), `smartvibes-dev` (the `dev` environment) and `smartvibes-prod` (the `prod` environment). Log in with `aws sso login --profile smartvibes-dev`. Check which account a profile points at with `aws sts get-caller-identity --profile <name>` before changing anything.
- One CDK stack per environment, in its own account: `SmartvibesSongwriter-dev`, `SmartvibesSongwriter-prod`. Each account also has a `SmartvibesSongwriter-github` stack (GitHub deploy role; deploy with `-c env=<env>`). Resource names follow `smartvibes-songwriter-<env>-<resource>`. The DynamoDB table and Cognito user pool use `RETAIN`.
- Deploys normally run through the GitHub Deploy workflow. A merge to `main` deploys `dev` automatically with no approval; `prod` is run by hand from the Actions tab and needs the owner's approval. Only `main` deploys; there is no `develop` branch and feature branches do not deploy (ADR 0006). Use `scripts/new-env.sh <env>` only for the first deploy of an environment. Never deploy to the wrong account: always pass the matching `--profile`.
- Real Cognito and API values live in the git-ignored `frontend/.env.local` (points at `dev`). Never commit secrets, API keys, or `.env.local`.
- Every AI call must go through the token-budget checkpoint described in the plan. No route may call the Anthropic API directly.
