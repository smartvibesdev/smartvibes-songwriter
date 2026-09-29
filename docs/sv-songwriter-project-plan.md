# Songwriting Companion: Project Plan

> Working title. Rename freely.

An AI-assisted notebook for singer-songwriters. Users save song fragments and full songs, search their own catalog, and use AI tools to get unstuck: metaphors, similes, idioms, synonyms, near-rhymes, editing suggestions, constraint-based idea generation, and drafts built from their own saved fragments.

The app is public, so **cost control is a first-class feature**, not an afterthought.

---

## 1. Goals

**Portfolio goals**

- Show a real full-stack AI application: React front end, Python back end, real database, deployed on AWS.
- Show production thinking around AI: token budgets, abuse protection, cost caps, structured output, and quality checks.
- Be useful to the author (a working songwriting tool) and distinctive enough to avoid the generic "chatbot" portfolio project.

**Non-goals**

- Not a music generator (no audio, no melody).
- Not a social platform (no sharing, comments, or feeds in v1).
- Not a multi-tenant SaaS with billing.
- No micro frontend architecture in v1 (optional stretch, see section 10).

---

## 2. Signature features

These are what make the project stand out. Protect them when scope gets tight.

1. **Works from your own catalog.** The AI resurfaces relevant old fragments and drafts new songs using the user's own material (retrieval-augmented generation, RAG).
2. **Constraint-based idea generation.** Claude's temperature range is 0 to 1, so instead of cranking randomness, feed the model random seed words, forced perspectives, and odd constraints (in the spirit of Eno's *Oblique Strategies*).
3. **Visible token meter.** The UI shows each user's remaining daily AI budget and how many tokens each action used.
4. **Near-rhyme finder with no AI.** Phonetic lookup (for example, "home" / "stone") costs zero tokens. Use AI only where it adds value.
5. **MCP server for direct access from Claude.** A Model Context Protocol server exposes fragment operations (add a fragment, search fragments, maybe "draft using my fragments") so Claude itself can read and write to the app's data, separate from the web UI. This is a current, resume-relevant skill on its own, and it reuses the same backend logic as the web app rather than duplicating it. Not every MCP operation costs tokens — adding or searching fragments is plain data access and should be called out in the write-up as an example of AI-adjacent work that doesn't burn budget.

---

## 3. Scope

### MVP (weeks 1 to 3)

- Sign in with Google
- Create, edit, and delete songs
- Create, edit, and delete fragments
- Keyword search across fragments and songs
- One AI tool (metaphor suggestions) behind the token checkpoint
- Daily per-user token budget and global spend cap

### Full v1 (weeks 4 to 6)

- Search by meaning (embeddings)
- "Draft a song from my fragments"
- Remaining AI tools: simile, idiom, synonym, antonym, editor
- Constraint-based idea generator
- Near-rhyme finder
- Token meter in the UI
- Invite codes with larger budgets for recruiters
- MCP server exposing fragment add/search (and later, draft-from-fragments) to Claude directly

### Later (only if time allows)

- Export songs to PDF or text
- Version history for songs
- Tags and collections for fragments

---

## 4. Architecture

```
Browser (React + TypeScript)
   │  HTTPS
   ▼
CloudFront + S3 (static front end)
   │
   ▼
API Gateway (rate limiting, JWT authorizer via Cognito)
   │
   ▼
AWS Lambda (Python, FastAPI via Mangum)
   ├── DynamoDB   (users, songs, fragments, usage counters, invites)
   ├── Secrets Manager (Anthropic API key)
   ├── Anthropic API  (Claude Haiku 4.5, Claude Sonnet 5)
   └── Embedding service (see decisions, section 9)

MCP server (Python)
   │  reuses the same backend service functions as the FastAPI app
   ▼
DynamoDB (fragments, songs)
```

The MCP server is a second, thin interface into the same fragment/song service layer used by the web app — not a separate copy of the logic. This is worth calling out in the README and in interviews as a "one core service, two interfaces" design choice.

### Tech stack

| Layer | Choice | Why |
|---|---|---|
| Front end | React + TypeScript + Vite | Largest hiring demand; good ecosystem for streaming UIs |
| Back end | Python 3.12, FastAPI | Real Python API, typed, auto-generated docs |
| Hosting | AWS Lambda + API Gateway | Near-zero cost when idle |
| Database | DynamoDB | Cheap, serverless, atomic counters for quotas |
| Auth | Amazon Cognito + Google sign-in | Standard, avoids hand-rolled auth |
| AI (small tools) | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) | Fast and cheap |
| AI (drafting) | Claude Sonnet 5 (`claude-sonnet-5`) | Better quality for long output |
| Infrastructure | AWS CDK (Python) | Repeatable, reviewable infrastructure |
| CI/CD | GitHub Actions | Deploy on merge to main |
| Tests | pytest, Vitest, Playwright (one smoke test) | Enough to show discipline |
| MCP server | Python, official MCP SDK | Lets Claude add/search fragments directly; calls the same backend service functions as the web app |

---

## 5. Data model (DynamoDB, single table)

| Entity | PK | SK | Key attributes |
|---|---|---|---|
| User profile | `USER#<id>` | `PROFILE` | email, created_at, invite_code, daily_budget |
| Song | `USER#<id>` | `SONG#<id>` | title, body, updated_at |
| Fragment | `USER#<id>` | `FRAG#<id>` | text, tags, embedding (later), updated_at |
| User usage | `USER#<id>` | `USAGE#<YYYY-MM-DD>` | tokens_used, tokens_reserved, ttl |
| Global usage | `GLOBAL` | `USAGE#<YYYY-MM-DD>` | tokens_used, ttl |
| Invite code | `INVITE#<code>` | `META` | daily_budget, expires_at, uses |

Notes:

- Usage items use DynamoDB TTL so old counters clean themselves up.
- With a few hundred fragments per user, embeddings can live on the fragment item and similarity can be computed in Python. Document the scale-up path (a vector database) in an ADR.

---

## 6. Token budget design

Every AI feature goes through **one checkpoint** in the back end. No route may call the Anthropic API directly.

### Flow

1. **Validate input.** Enforce a maximum input length per tool.
2. **Estimate cost.** Input tokens (estimated) plus the `max_tokens` ceiling set for that tool.
3. **Reserve.** Do an atomic conditional update in DynamoDB: add the estimate to `tokens_reserved` only if `tokens_used + tokens_reserved + estimate <= daily_budget`. Do the same check against the global counter. Reject with HTTP 429 if either fails.
4. **Call Claude** with the tool's fixed `max_tokens`.
5. **Reconcile.** Read actual `usage.input_tokens` and `usage.output_tokens` from the response, add them to `tokens_used`, and release the reservation.
6. **Return** the result plus the user's remaining budget for the token meter.

### Layers of protection

| Layer | Purpose |
|---|---|
| Per-user daily token budget | Stops one user from burning the budget |
| Per-tool `max_tokens` and input caps | Bounds worst-case cost of a single call |
| Global daily token cap (circuit breaker) | AI features pause when hit; everything else still works |
| API Gateway throttling | Stops request floods |
| Authentication required | No anonymous AI calls |
| Invite codes | Recruiters get a bigger budget without opening the door for everyone |
| AWS Budgets alarm | Email alert on unexpected AWS spend |
| Anthropic console spend limit | Hard ceiling at the provider |
| Cheapest adequate model per tool | Haiku for small tools, Sonnet only for drafts |

---

## 7. Security and abuse considerations

- Store the Anthropic API key in AWS Secrets Manager. Never commit secrets. Never expose the key to the browser.
- Render AI output as plain text, not HTML, to avoid injection.
- Treat user-saved text as untrusted input to the model (prompt injection). Keep system prompts separate and instruct the model to use fragments only as source material.
- Instruct the model to write original material and not reproduce existing songs' lyrics.
- Validate all request bodies (Pydantic models).
- Least-privilege IAM roles for Lambda.
- CORS locked to the app's own domain.
- MCP server authenticates the same way as the web app (no separate, weaker auth path) and still goes through the token checkpoint for any operation that calls Claude.

---

## 8. Quality checks for the AI features

A lightweight evaluation set is a differentiator. Keep it small.

- Have each tool return **structured JSON** (validated with Pydantic) so output shape can be tested.
- Create a `evals/` folder with about 20 sample inputs per tool.
- Automated checks: valid JSON, expected number of suggestions, length limits, no leaked system prompt.
- Track tokens per call and cost per tool. Report them in the README.
- Manual review of a sample of outputs, with notes on prompt changes that improved quality.

---

## 9. Open decisions (record each as an ADR in `docs/adr/`)

| Decision | Options | Decide by |
|---|---|---|
| Claude access | Anthropic API directly vs. Amazon Bedrock | Week 3 |
| Embeddings | Voyage AI vs. Amazon Bedrock embedding models (Claude does not produce embeddings) | Week 4 |
| Repo location | Personal GitHub vs. company GitHub organization | Week 1 |
| Domain name | Custom domain vs. default CloudFront URL | Week 5 |
| License | MIT (permissive) is the default suggestion | Week 1 |

---

## 10. Schedule (about 5 to 6 weeks, working around the job search)

| Week | Goal | Done when |
|---|---|---|
| 1 | Repo, CDK infrastructure, Cognito sign-in, "hello world" deployed end to end | A signed-in user sees a page served from AWS that calls the API |
| 2 | Songs and fragments CRUD, keyword search | User can save and find songs and fragments |
| 3 | Metaphor tool and the token checkpoint (reserve, call, reconcile); MCP server exposing add/search fragments | Budget is enforced; 429 returned when exhausted. Claude can add and search fragments through the MCP server |
| 4 | Embeddings, search by meaning, "draft a song from my fragments" | Draft uses relevant saved fragments |
| 5 | Remaining tools, constraint-based ideas, near-rhymes, token meter, invite codes | All v1 features working |
| 6 | Tests, eval set, architecture diagram, demo video, write-up | Portfolio deliverables complete |

**Optional stretch:** split the UI into a small micro frontend (for example, the fragment browser as a separately deployed module) to demonstrate the pattern. Only after week 6.

### Week 1 checklist

- [ ] Create the repo (see decision above), add README, LICENSE, `.gitignore`
- [ ] Set up `frontend/`, `backend/`, `infra/`, `docs/`, `evals/` folders
- [ ] AWS account hygiene: MFA, a budget alarm, a non-root deployment user or role
- [ ] CDK stack: S3 + CloudFront, API Gateway, Lambda, DynamoDB table, Cognito user pool
- [ ] Anthropic account: create an API key, set a monthly spend limit
- [ ] FastAPI "health" endpoint deployed behind API Gateway
- [ ] React app with Google sign-in calling an authenticated endpoint
- [ ] GitHub Actions: lint, test, deploy on merge to main
- [ ] First ADR written

---

## 11. Portfolio deliverables

- Live demo link with invite-code access for recruiters
- README with architecture diagram, screenshots, and a "how token limiting works" section
- ADRs documenting the decisions in section 9
- A 2 to 3 minute demo video
- A short write-up: "How I keep a public AI app from running up my bill"
- Eval results and cost-per-tool table

---

## 12. Definition of done (v1)

- Deployed on AWS with infrastructure fully defined in code
- A stranger can sign in, save songs and fragments, and use every AI tool
- No path exists to call the model without passing the token checkpoint
- Global cap and per-user caps verified by tests
- Documentation complete enough that someone else could deploy it
