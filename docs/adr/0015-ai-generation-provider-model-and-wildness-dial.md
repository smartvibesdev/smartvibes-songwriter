# 0015. AI generation: provider, model and the wildness dial

- Status: Accepted (model amended 2026-10-04: Sonnet 4.6 instead of Haiku 4.5, at the owner's request)
- Date: 2026-10-04

## Context

The next feature is AI generation in the song editor: a title, lyrics or a fragment, from an
optional seed text or from nothing, with a control that goes from "predictable" to "wild".
The plan (section 6) already requires every AI call to pass one token checkpoint (reserve, call,
reconcile) and lists "Claude API directly or Amazon Bedrock" as a decision due in week 3.

Facts that shape the design (from the Claude API reference, cached 2026-09-25):

- Claude's temperature runs from 0 to 1, not 0 to 2 (that range is OpenAI's).
- The newest models (Opus 5.5, Sonnet 5.5, Sonnet 5, Fable 5.1 and others) reject any
  non-default `temperature`, `top_p` or `top_k` with a 400 error. Haiku 4.5, Sonnet 4.5 and
  4.6, and Opus 4.5 and 4.6 still accept them.
- Haiku 4.5 costs $1 per million input tokens and $5 per million output tokens. Sonnet 4.6
  costs $3 and $15. Sonnet 5.5 costs $2 and $10.
- A temperature of 1 gives varied text, not gibberish, so "wild" needs more than temperature.

## Options considered

Provider:

- **Claude API directly (Anthropic Python SDK).** New models and features first, simple client,
  matches the plan's architecture diagram. The API key must be kept in AWS Secrets Manager.
- **Amazon Bedrock.** No API key (uses the Lambda's IAM role) and billing through AWS, but
  newer models and features can arrive later, and the client differs from the first-party one.

Wildness dial:

- **Real temperature only.** Simple, but it works only on models that accept it, and its top end
  is still tame.
- **Prompt constraints only** (random seed words, forced odd perspectives, odd constraints, in
  the spirit of Oblique Strategies). Works on every model, but the low end is not truly
  deterministic.
- **Both** (chosen).

## Decision

- Call the **Claude API directly** with the Anthropic Python SDK. The key lives in Secrets
  Manager, is read by the Lambda only, and never reaches the browser.
- Use **`claude-sonnet-4-6`** for generation: the newest Sonnet that accepts temperature, and
  better writing than Haiku. (The first version of this ADR chose Haiku 4.5, the cheapest model
  that accepts temperature; the owner chose Sonnet 4.6 for quality.) The model ID is one
  constant, so it can change in one place.
- The dial is **0 to 10** in the UI:
  - 0: temperature 0 and a plain, literal instruction;
  - 1 to 7: temperature rises evenly from 0 to 1;
  - 8 to 10: temperature 1, plus prompt constraints that grow with the dial (random seed words,
    a forced unusual viewpoint, a strange constraint).
  If the model is ever changed to one that rejects temperature, the dial keeps working through
  the prompt constraints alone.
- Every call goes through the **token checkpoint** from the plan: validate input length, estimate
  cost, reserve atomically in DynamoDB against the user's daily budget and the global cap
  (HTTP 429 when either is exhausted), call Claude with the tool's fixed `max_tokens`, then
  reconcile with the real `usage` numbers. The response includes the remaining budget for the
  token meter. No route calls Claude directly.
- One endpoint, `POST /ai/generate`, takes the kind (`title`, `lyrics` or `fragment`), an optional
  seed text, and the dial value, and returns the generated text for the user to accept or discard.
  Nothing is saved without the user choosing to.
- Tests use a fake Claude client, so the checkpoint and the endpoint are tested without spend.

## Consequences

- A typical lyrics request (about 500 input and 700 output tokens) costs 1 to 2 cents on Sonnet
  4.6. The daily budget and global cap bound the worst case: about $0.75 a day for one user and
  $7.50 a day for everyone, if every token were output.
- Sonnet 5 and later cannot take a temperature. Moving to them would leave the dial working
  through the prompt constraints only. Switching is one constant, but it is a decision to make
  on purpose.
- Before the first deploy the owner must create an Anthropic API key and set a monthly spend
  limit there. Storing the key in Secrets Manager and granting the Lambda read access are AWS
  changes that need an approved CDK deploy.
- The token meter, per-user budgets and invite codes from the plan build on this checkpoint.
- Embeddings (finding fragments that fit a song) remain a separate decision.
