# Plan: AI answers that use each user's own fragments (RAG)

- Status: **Plan only. Nothing is built.** A decision record (ADR 0019) will follow once the "To verify" items below are checked.
- Date: 2026-10-10

## The goal, in plain words

A user writes a song and asks the assistant for help. The assistant first looks through **that user's own saved fragments**, picks the few closest in meaning to what they are writing, and uses them as inspiration. The reply shows which fragments it used, so the user can see where the ideas came from.

Every user has their own fragments. One user must never see, or get AI help from, another user's fragments.

This technique is called **RAG** (retrieval-augmented generation): first retrieve relevant material, then let the AI generate with that material in front of it.

## Words used in this plan

- **Embedding:** a list of numbers that represents the meaning of a piece of text. Texts with similar meaning get similar numbers.
- **Vector:** another name for that list of numbers.
- **Vector store:** a database that can answer "which stored vectors are closest to this one?"
- **Amazon Bedrock:** AWS's service for calling AI models from inside AWS. We would use it to turn text into embeddings (model: Titan Text Embeddings V2).
- **Amazon S3 Vectors:** a vector store built into S3. It is serverless (no servers to run), billed by use, and can filter results by metadata.
- **DynamoDB Streams:** a feed of every change to a DynamoDB table (item added, changed, deleted) that can trigger a Lambda function.

## How it would work

**1. Keeping the vectors up to date (runs by itself when a fragment changes):**

```
user saves, edits or deletes a fragment
  -> the DynamoDB table changes
  -> DynamoDB Streams triggers the "sync" Lambda
  -> sync Lambda asks Bedrock to embed the fragment text
  -> sync Lambda writes (or replaces, or deletes) the vector in S3 Vectors,
     labeled with the fragment's id and its OWNER's user id
```

There is one stream and one sync Lambda for all users. The table key already holds the owner (`USER#<id>`), so the Lambda reads the owner from the record. The table also holds songs and token counters, so the Lambda ignores everything that is not a fragment.

**2. Using the vectors (runs when the user asks the assistant for help):**

```
user asks the assistant (for example, "use my fragments to write a verse about rain")
  -> backend takes the user id from the verified sign-in token
  -> backend asks Bedrock to embed the user's request and current lyrics
  -> backend queries S3 Vectors for the closest vectors, FILTERED to that user id
  -> backend reads the matching fragments' text
  -> the assistant (Claude) gets the fragments as extra context and writes the reply
  -> the reply includes the fragments it used, shown as clickable chips
```

This fits our existing assistant: retrieval becomes one more tool (`search_fragments`) next to `edit_lyrics`, `set_title` and `lookup_words` in `backend/app/ai/chat.py`. It goes through the same token budget.

## Decisions so far

| Question | Choice | Why |
| --- | --- | --- |
| Where do embeddings come from? | Bedrock, Titan Text Embeddings V2 | Stays inside AWS (no data leaving AWS), uses IAM instead of an API key. Anthropic has no embedding model. |
| Where are vectors stored? | S3 Vectors (to verify, see below) | Cheap, serverless, filterable by owner. OpenSearch Serverless costs a few hundred dollars a month at minimum. DynamoDB has no similarity search. |
| One pipeline per user? | No. One stream, one Lambda, all users | Every vector carries its owner's id, and every search filters on it. |
| What is searched? | Fragments only, for now | Songs could be added later. |
| How is it used? | As an assistant tool, with a "sources" list | Fits the existing chat and token budget. |

## Privacy rules (the most important part)

1. Every vector stores `user_id` as metadata. It comes from the table record, never from the browser.
2. Every search is filtered by the `user_id` from the verified sign-in token. The browser cannot choose it.
3. Edits and deletes are synced too, so an old or deleted fragment cannot come back in a search.
4. A required test: create fragments for two users, and check that each user's search returns only their own.
5. If a user is ever deleted, their vectors can be found by `user_id` and removed.

## What changes in the codebase

- **Infrastructure (`infra/`, CDK):** turn on the stream for the table; a new sync Lambda; an S3 Vectors bucket and index; IAM permissions for the Lambdas to call Bedrock and read and write the vectors.
- **Backend (`backend/`):** an embedding module (Bedrock); a vector-store module (S3 Vectors); the sync Lambda handler; a `search_fragments` tool in the chat; a backfill script for the existing fragments; tests that use a fake embedder and a fake vector store, so tests spend nothing.
- **Frontend (`frontend/`):** show the used fragments as chips under an assistant reply, and maybe a "use my fragments" toggle.
- **Docs:** ADR 0019 (this decision), and a note in ADR 0018.

Existing tables, routes and screens keep working as they are.

## To verify before building

1. Is S3 Vectors available in us-east-1, and what are its price and limits (vector size, metadata filtering, query speed)? Fallback: Pinecone's free tier, or keeping vectors in DynamoDB and comparing them in code.
2. Turn on Bedrock model access for Titan Text Embeddings V2 in both AWS accounts (dev and prod). This is a one-time setup step in the console.
3. Choose the vector size (for example 512 numbers per fragment), the number of fragments to retrieve (3 to 5), and whether to ignore matches that are not close enough.
4. Should Claude also move to Bedrock (no API key, all traffic inside AWS)? That would mean revisiting ADR 0015. The model choice stays the owner's decision.
5. Do the sync in a stream, or compute the embedding in the save route? The stream is more to build and shows off more AWS; the save route is simpler. The stream is the plan unless it proves too heavy.

## Build order (one branch each)

1. ADR 0019, after the checks above.
2. Embedding module and vector-store module, with tests using fakes.
3. Infrastructure: stream, sync Lambda, vector bucket and index, permissions. Needs the owner's approval to deploy.
4. Backfill script for the 5,000+ existing fragments (dry run first, as with the importer).
5. The `search_fragments` assistant tool, and the sources chips in the UI.
6. A small retrieval-quality check: about 20 sample fragments and queries, with the expected matches written down.

## Cost note

Embedding a fragment costs a tiny fraction of a cent, so a few thousand fragments cost cents to embed, and each assistant question adds one embedding call plus one search. S3 Vectors bills by storage and queries. At this size the expected cost is a few cents a month, to be confirmed with the real prices in "To verify" step 1.

## What was dropped from the Gemini blueprint this plan started from

- Separate `FragmentsTable` and `SongsTable` (we have one table).
- It had no per-user filter, which is a privacy bug.
- It synced only new fragments, so edits and deletes would have been wrong.
- It called Claude directly through Bedrock, skipping the token budget, with an outdated model.
- It suggested OpenSearch Serverless, which costs too much for this project.
- Its "do not touch existing code" rule can't hold, because we need CDK, backend and UI changes.

## Portfolio talking points

- An event-driven pipeline (stream, Lambda, vector store) that stays in sync on create, edit and delete.
- Multi-user data isolation, proved by a test.
- AI grounded in the user's own notes, with visible sources.
- Cost control: a token budget, a serverless store, and a plan that avoids a fixed monthly cost.
