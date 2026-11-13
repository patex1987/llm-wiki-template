---
title: Karpathy LLM Wiki
type: source
tags:
  - llm-wiki
  - knowledge-base
status: stable
created: 2026-11-13
updated: 2026-11-13
aliases: []
related:
  - LLM Wiki
sources:
  - raw/external-sources/2026-11-13-karpathy-llm-wiki-excerpts.md
  - https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
reviewed: 2026-11-13
volatility: high
---

# Karpathy LLM Wiki

## Summary

An "idea file" by Andrej Karpathy describing a pattern: instead of retrieving raw document chunks at question time (RAG), have an LLM agent incrementally build and maintain a persistent, interlinked Markdown wiki between the human and the raw sources. It is deliberately abstract and meant to be pasted into your own agent, which then works out the specifics with you.

## What the source claims

- RAG-style tools rediscover knowledge from scratch on each question, so nothing accumulates.
- A maintained wiki compounds: cross-references exist, contradictions are flagged, synthesis reflects everything ingested.
- Three layers: immutable raw sources, an LLM-owned wiki, and a schema file (`CLAUDE.md` / `AGENTS.md`) that makes the LLM a disciplined maintainer.
- Three operations: ingest, query (with good answers filed back), lint.
- Two navigation files: a content-oriented `index.md` and an append-only `log.md` with greppable headings.
- The index-first approach works "at moderate scale (~100 sources, ~hundreds of pages)"; beyond that, add a search tool such as qmd.

## Evidence quality

A single practitioner's design note, not a benchmarked method. It reports no measurements. Treat the scale figures as the author's experience, not a limit proven by test.

## What this source fed

- [[LLM Wiki]]

## Related

- [[LLM Wiki]]

## Sources

- [Primary reference](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- `raw/external-sources/2026-11-13-karpathy-llm-wiki-excerpts.md`
