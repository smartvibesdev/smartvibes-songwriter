I'm building an AI portfolio project called "SmartVibes Songwriter" — a songwriting companion app for singer-songwriters. Full plan is in PROJECT_PLAN.md in this repo — please read it first.

Quick summary: React + TypeScript front end, Python (FastAPI) backend on AWS Lambda, DynamoDB, Cognito auth, deployed via AWS CDK (Python). Key features: save/search song fragments and songs, AI writing tools (metaphor, simile, etc.) via Claude, a token/cost budget system since it's public-facing, and an MCP server exposing fragment add/search to Claude directly.

Let's start with Week 1 from the plan:

Set up the folder structure: frontend/, backend/, infra/, docs/, evals/
Scaffold a basic CDK stack (Python) with S3 + CloudFront, API Gateway, a Lambda function, a DynamoDB table, and a Cognito user pool — matching the architecture in the plan's section 4
Scaffold a minimal FastAPI app in backend/ with a single /health endpoint
Scaffold a minimal Vite + React + TypeScript app in frontend/

Don't deploy anything yet — let's get the code scaffolded and reviewed first, then deploy once I've confirmed the AWS account is set up. Ask me before making any AWS-related assumptions (region, account, naming conventions).