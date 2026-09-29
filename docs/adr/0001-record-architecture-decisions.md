# 0001. Record architecture decisions

- Status: Accepted
- Date: 2026-09-29

## Context

The project plan lists several open technical decisions (Claude access,
embeddings, domain name, and others). This is a portfolio project, so the
reasoning behind each choice is as valuable as the choice itself.

## Options considered

- Keep decisions in the project plan or in commit messages: easy, but the
  reasoning gets lost or buried.
- One short Architecture Decision Record (ADR) per decision in `docs/adr/`:
  small overhead, searchable, and reviewable in pull requests.

## Decision

Use ADRs, one file per decision, following `0000-template.md`.

## Consequences

Each open decision in section 9 of the project plan gets an ADR when it is
made. Reversing a decision means writing a new ADR, not editing history.
