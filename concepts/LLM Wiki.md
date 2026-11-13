---
title: LLM Wiki
type: concept
tags:
  - llm-wiki
  - knowledge-base
status: stable
created: 2026-11-13
updated: 2026-11-13
aliases:
  - Persistent LLM Wiki
related:
  - Karpathy LLM Wiki
sources:
  - Karpathy LLM Wiki
reviewed: 2026-11-13
volatility: high
---

# LLM Wiki

## Summary

An LLM Wiki is a folder of interlinked Markdown notes that an LLM agent writes and maintains, sitting between immutable raw sources and the questions you ask later. Knowledge is integrated once at ingest time instead of being re-derived from raw chunks on every query. (Source claim: [[Karpathy LLM Wiki]]. The rest of this page is KB synthesis unless marked.)

## Problem

Document-chat and RAG setups answer each question by retrieving fragments and synthesizing from scratch. A question that needs five documents re-does the same cross-document reasoning every time, and nothing learned from the previous answer is kept. Human-maintained wikis fail for the opposite reason: the bookkeeping (cross-references, consistency, summaries) grows faster than the value, so people stop.

## Core idea

Split the system into three layers with different owners:

| Layer | Owner | Mutability |
| --- | --- | --- |
| Raw sources (`raw/`) | Human curates | Immutable |
| Wiki (`concepts/`, `patterns/`, `sources/`, ...) | LLM writes | Continuously updated |
| Schema (`AGENTS.md`, skills) | Human + LLM co-evolve | Versioned |

Three operations keep it alive:

- **Ingest**: read a source, write a source summary, extend or create topic notes, update `index.md`, append to `log.md`. One source may touch many notes.
- **Query**: search, read a few notes, answer with citations; file reusable answers back as new notes.
- **Lint**: find broken links, orphans, contradictions, stale claims, missing pages.

Why it works: the costly part of a knowledge base is bookkeeping, not thinking, and an agent can touch many files per pass at near-zero marginal cost. The assumption is that the agent's edits are reviewable and mostly right; the human stays the curator of sources and the judge of claims.

Worked example (hypothetical): you add an article on database connection pooling. The agent searches for existing notes, finds `Connection Pooling` and `Postgres Operations`, extends the first with a new failure mode, records a contradiction in the second because the article disagrees on a default, creates a source summary, and logs the ingest. Next month a question about "why do requests hang under load" is answered from those already-linked notes.

## When to use

- Knowledge accumulates over weeks or months (research topic, book, engineering practices, team knowledge).
- You want synthesis and cross-links, not only passage lookup.
- You can review diffs (git) and tolerate occasional agent mistakes.

## When not to use

- A one-off question over a few documents: plain retrieval is cheaper.
- Content that must be quoted verbatim or audited as-is: keep it in `raw/`, do not rely on paraphrase.
- Very large or fast-changing corpora, where index-first navigation and per-ingest page updates may stop scaling (see Implementation notes).

## Implementation notes

- Keep `raw/` immutable so every wiki claim can be traced to a source.
- Make the schema file explicit about page format, linking rules, and the ingest/query/lint procedures; this is what separates a disciplined maintainer from a chatbot.
- Distinguish source claims, synthesis, and examples in the text, otherwise LLM inference slowly becomes "fact".
- Scale caveat (source claim plus inference): the source says the index-first approach works at about 100 sources and hundreds of pages. This template keeps the index and log out of routine reads (`kb.py search`, tail-only log appends) to push that limit out, but cost per ingest, error accumulation, and multi-user editing remain open problems. See the README section on limits.

## Related

- [[Karpathy LLM Wiki]]

## Sources

- [[Karpathy LLM Wiki]]
