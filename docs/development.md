# Developer guide: getting started

Step-by-step instructions for working on this project, written for someone who
has not used Python virtual environments before.

## What is in the repo

| Folder | What it is | Language | Needs a Python virtual environment? |
| ------ | ---------- | -------- | ----------------------------------- |
| `frontend/` | The web app (React, Vite) | TypeScript | No (uses `npm`) |
| `backend/` | The API (FastAPI, runs on AWS Lambda) | Python | Yes |
| `infra/` | AWS infrastructure defined as code (CDK) | Python | Yes |
| `docs/` | Notes, decision records (`adr/`), deployment notes | Markdown | No |
| `evals/` | Quality checks for AI features (empty for now) | | |

## Install once (prerequisites)

- **Git**
- **Python 3.12 or newer** (`python3 --version`)
- **Node.js 22 or newer** (`node --version`)
- **AWS CLI** and **AWS CDK** (only needed to deploy): `brew install awscli aws-cdk`
- An AWS login. See [deployment.md](deployment.md).

## What is a "virtual environment" (the `(.venv)` in your prompt)?

Python projects install their libraries into a private folder called `.venv`
instead of installing them system-wide. You "activate" it in a terminal window
to tell that window to use those libraries. When it is active, your prompt
starts with `(.venv)`.

**Rule of thumb:** activate the virtual environment for the folder you are
working in whenever you run Python tools: `pytest`, `ruff`, `uvicorn`, or any
`cdk` command. You do not need it for `npm` commands.

**How you know you need it:** you get an error such as `command not found:
pytest` or `ModuleNotFoundError`, or your prompt does not show `(.venv)`.

- Turn it on (from inside `backend/` or `infra/`): `source .venv/bin/activate`
- Turn it off: `deactivate`
- Each Python folder has its own `.venv`. Activating one and then working in
  the other folder uses the wrong libraries. If in doubt, `deactivate`, then
  `cd` to the folder you want and activate that one.
- Opening a new terminal window starts with no environment active.

## First-time setup (once per computer)

Run these from the repo root.

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
deactivate
cd ..

# Infrastructure
cd infra
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..

# Frontend
cd frontend
npm install
cd ..
```

Then create `frontend/.env.local` (this file is git-ignored). Copy
`frontend/.env.example` and fill in the values; see
[deployment.md](deployment.md) for where to get them.

## Every day: start working

1. Open the repo folder in Visual Studio Code (**File > Open Folder**).
2. Open the built-in terminal: **Terminal > New Terminal** (or Ctrl+`).
   Use the `+` in the terminal panel to open more windows. You will usually
   want one per task below.

### Run the backend locally

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

Open <http://localhost:8000/health>. You should see `{"status":"ok"}`.
Interactive API docs are at <http://localhost:8000/docs>. Stop it with Ctrl+C.

Note: `/me`, `/songs`, `/fragments` and `/search` all return 401 when run
locally, because the login check is done by AWS API Gateway, which is not
present on your computer. The tests (`pytest`) cover those routes with a
simulated login and a fake DynamoDB, so you do not need AWS to run them. To try
the real routes, deploy to `dev` and call them with a signed-in token.

### Run the frontend locally

In a second terminal:

```bash
cd frontend
npm run dev
```

Open the address it prints (normally <http://localhost:5173>). By default the
page talks to the deployed API (from `VITE_API_URL` in `.env.local`). To use
your local backend instead, set `VITE_API_URL=http://localhost:8000`, then
restart `npm run dev`.

### Try the app locally with sample data

The real API checks sign-in through AWS, so on its own it returns 401 for songs and
fragments on your computer. `backend/dev_server.py` runs the real API code on a fake
in-memory database (`moto`) with a pretend signed-in user and some sample songs and
fragments. Nothing touches AWS, and nothing is saved: stop it and the data is gone.

```bash
# Terminal 1: the API, with sample data (http://127.0.0.1:8000)
cd backend && source .venv/bin/activate
python dev_server.py

# Terminal 2: the web app, pointed at that API (http://localhost:5173)
cd frontend
VITE_API_URL=http://localhost:8000 npm run dev
```

To try the lists, filters and paging at scale, start the API with `python dev_server.py --big`.
It adds 5,000 generated fragments and 300 songs spread over 2018 to now. The fake database is
slower than the real one, so pages take a few seconds to load; that is not what AWS will feel like.

Open <http://localhost:5173/__preview-login>. That page pretends you are signed in and
sends you to the app. It exists only in the dev server, and only when `VITE_API_URL`
points at localhost; it is never part of a production build. The API ignores the
token, so there is nothing to type.

Clicking Sign out in this mode may take you to the real Cognito sign-out page
(harmless). Open the `__preview-login` link again to get back in.

### Run the checks (same ones CI runs on GitHub)

```bash
# Backend
cd backend && source .venv/bin/activate
pytest
ruff check .
ruff format --check .      # or `ruff format .` to fix formatting

# Frontend
cd frontend
npm run lint
npm run build
npm run format:check       # or `npm run format` to fix (Prettier)

# Infrastructure (confirms the stack still builds; touches nothing in AWS)
cd infra && source .venv/bin/activate
python app.py
```

TypeScript code style (Prettier settings and the rules for `if`, braces, blank
lines and positive logic) is in the "TypeScript style" section of
[CLAUDE.md](../CLAUDE.md).

## Deploying to AWS

See [deployment.md](deployment.md). Normally you do not deploy by hand:
merging to `main` deploys `dev` through GitHub Actions, and you run the Deploy
workflow from the Actions tab to deploy `prod`. Each environment lives in its own
AWS account (profiles `smartvibes-dev` and `smartvibes-prod`).

## Making changes (Git)

Work on a branch, not directly on `main`:

```bash
git checkout main && git pull
git checkout -b my-change
# ...edit, then...
git add <files>
git commit -m "Describe the change"
git push -u origin my-change
```

Then open a pull request on GitHub. CI runs the checks above; merge when they
pass. This repo commits as the `smartvibesdev` GitHub identity (set with
`git config user.email` inside the repo).
