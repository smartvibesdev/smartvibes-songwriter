# smartvibes-songwriter

AI-assisted songwriting app for singer-songwriters: save fragments, generate ideas, and search your catalog by meaning. React, Python, AWS.

## Where to start

- **Setting up and running the project:** [docs/development.md](docs/development.md)
- **AWS deployment and operations:** [docs/deployment.md](docs/deployment.md)
- **How the AWS account and deploys were set up, with fixes for problems hit:** [docs/aws-setup-runbook.md](docs/aws-setup-runbook.md)
- **Project plan:** [docs/sv-songwriter-project-plan.md](docs/sv-songwriter-project-plan.md)
- **Architecture decisions:** [docs/adr/](docs/adr/)

## Layout

| Folder | Purpose |
| ------ | ------- |
| `frontend/` | React + TypeScript web app (Vite) |
| `backend/` | FastAPI API, runs on AWS Lambda |
| `infra/` | AWS CDK (Python) infrastructure |
| `docs/` | Plan, decision records, guides |
| `evals/` | Quality checks for AI features |
