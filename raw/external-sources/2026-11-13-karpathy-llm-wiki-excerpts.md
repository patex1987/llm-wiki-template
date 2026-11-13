# Karpathy, "LLM Wiki" (excerpts)

- Origin: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Captured: 2026-11-13
- Kind: secondary (author's idea file, not a specification)
- Note: short excerpts only, quoted for study. The full text lives at the link above.

> Instead of just retrieving from raw documents at query time, the LLM **incrementally builds and maintains a persistent wiki** — a structured, interlinked collection of markdown files that sits between you and the raw sources.

> The wiki is a persistent, compounding artifact. The cross-references are already there. The contradictions have already been flagged.

> There are three layers: **Raw sources** ... **The wiki** ... **The schema** — a document (e.g. CLAUDE.md for Claude Code or AGENTS.md for Codex) that tells the LLM how the wiki is structured, what the conventions are, and what workflows to follow.

> **Ingest.** ... A single source might touch 10-15 wiki pages.

> **Query.** ... good answers can be filed back into the wiki as new pages.

> **Lint.** Periodically, ask the LLM to health-check the wiki. Look for: contradictions between pages, stale claims that newer sources have superseded, orphan pages with no inbound links, important concepts mentioned but lacking their own page, missing cross-references, data gaps.

> **index.md** ... works surprisingly well at moderate scale (~100 sources, ~hundreds of pages) and avoids the need for embedding-based RAG infrastructure.

> **log.md** is chronological. It's an append-only record ... if each entry starts with a consistent prefix (e.g. `## [2026-04-02] ingest | Article Title`), the log becomes parseable with simple unix tools.

> At some point you may want to build small tools that help the LLM operate on the wiki more efficiently. A search engine over the wiki pages is the most obvious one ... [qmd](https://github.com/tobi/qmd) is a good option.

> The tedious part of maintaining a knowledge base is not the reading or the thinking — it's the bookkeeping.

> This document is intentionally abstract. It describes the idea, not a specific implementation.
