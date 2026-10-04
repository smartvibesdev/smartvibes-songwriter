# 0015. AI generation: provider, model and the wildness dial

- Status: Proposed
- Date: 2026-10-04

## Context

The next feature is AI generation in the song editor: a title, lyrics or a fragment, from an
optional seed text or from nothing, with a control that goes from "predictable" to "wild".
The plan (section 6) already requires every AI call to pass one token checkpoint (reserve, call,
reconcile) and lists "Claude API directly or Amazon Bedrock" as a decision due in week 3.

Facts that shape the design (from the Claude API reference, cached 2026-09-25):

- Claude's temperature runs from 0 to 1, not 0 to 2 (that range is OpenAI's).
- The newest models (Opus 5.5, Sonnet 5.5, Sonnet 5, Fable 5.1 and others) reject any
  non-default `temperature`, `top_p` or `top_k` with a 400 error. Haiku 4.5 and the 4.6 models
  still accept them.
- Haiku 4.5 costs $1 per million input tokens and $5 per million output tokens. Sonnet 5.5
  costs $2 and $10.
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

## Decision (proposed)

- Call the **Claude API directly** with the Anthropic Python SDK. The key lives in Secrets
  Manager, is read by the Lambda only, and never reaches the browser.
- Use **`claude-haiku-4-5`** for generation: the cheapest model, and one that accepts
  temperature. The model ID is one constant, so it can change in one place.
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

- A typical lyrics request (about 500 input and 1,500 output tokens) costs under one cent on
  Haiku 4.5. The daily budget and global cap bound the worst case.
- Haiku's writing is plainer than a larger model's. If quality disappoints, switching the model
  constant to Sonnet 5.5 is one change, at the cost of losing real temperature (the prompt
  constraints still apply).
- Before the first deploy the owner must create an Anthropic API key and set a monthly spend
  limit there. Storing the key in Secrets Manager and granting the Lambda read access are AWS
  changes that need an approved CDK deploy.
- The token meter, per-user budgets and invite codes from the plan build on this checkpoint.
- Embeddings (finding fragments that fit a song) remain a separate decision.
