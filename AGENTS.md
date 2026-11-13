# LLM Wiki Agent Instructions

This repository is an LLM-maintained Markdown knowledge base following the LLM Wiki pattern (see `README.md`). It works as an Obsidian vault but does not require Obsidian.

> Template note: this file is the *schema*. Edit the Purpose, directory layout, and page rules to fit your domain. Keep the shared rules and workflows unless you replace the skills too.

## Purpose

Maintain a persistent, compounding wiki for <YOUR DOMAIN: e.g. backend engineering, a research topic, a book, a team's project knowledge>.

The human curates sources and asks questions. The agent maintains the wiki:

- ingest sources into atomic notes
- update related pages and backlinks
- flag contradictions and stale claims
- keep `index.md` and `log.md` current
- preserve raw sources without modifying them

## Directory Layout

```text
/
  README.md                 vault overview for humans
  AGENTS.md                 operating rules for coding agents
  index.md                  content-oriented catalog
  log.md                    chronological maintenance log
  concepts/                 reusable explanations and mental models
  patterns/                 procedures and recipes
  decisions/                decisions and personal/team defaults, with rationale
  snippets/                 templates and small worked examples
  sources/                  generated summaries of ingested sources
  raw/                      immutable source inputs
  templates/                note templates
  reviews/                  freshness review proposals awaiting approval
  .kb/kb.py                 search, graph, freshness, and lint CLI (stdlib Python)
  .kb/config.json           review intervals and tag-based volatility defaults
  .agents/skills/           workflow skills (.claude/skills links here)
```

## Page Rules

Every generated wiki page should have YAML frontmatter:

```yaml
---
title: ""
type: concept
tags: []
status: draft
created: YYYY-MM-DD
updated: YYYY-MM-DD
aliases: []
related: []
sources: []
reviewed: YYYY-MM-DD   # optional: last date the claims were checked against sources
volatility: medium     # optional: high | medium | low, how fast the topic goes stale
---
```

`updated` changes on any edit. `reviewed` changes only when the content was verified, so an edit that only fixes formatting does not reset freshness. When `volatility` is missing, `.kb/config.json` infers it from tags.

Use these `type` values unless there is a strong reason to add another:

- `concept`
- `pattern`
- `decision`
- `snippet`
- `source`
- `index`
- `log`
- `template`

Use these `status` values:

- `draft`: useful but still rough
- `stable`: good default reference
- `needs-review`: needs human or source verification
- `deprecated`: kept for history, not current guidance

## Content Quality

Self-contained means a reader can understand the mechanism and apply or evaluate the idea without opening the external source. Required headings are a structure, not proof of substantive content.

- Explain why the technique works and what assumptions it needs.
- For patterns, provide a concrete procedure, a worked example, and important failure or recovery behavior.
- For concepts, explain the useful distinctions and consequences, with an example where that helps understanding.
- Replace advice such as "test carefully" or "document decisions" with what should be tested or recorded and how to interpret the result.
- Distinguish source claims, KB synthesis, hypothetical examples, and locally verified behavior. More text must not turn an inference into a source claim.
- Read the completed article for usefulness; metadata, tags, links, and length checks cannot establish content quality.
- Prefer expanding or merging an existing note when a proposed new page adds no distinct reusable knowledge. Concise definitions, decisions, and source summaries can remain short when they fulfill their purpose.

## Linking

Prefer Obsidian links for wiki pages:

- `[[LLM Wiki]]`
- `[[Some Concept Name]]`
- `[[Some Concept Name|display text]]`

Use normal Markdown links for external sources.

Each concept or pattern page should include:

- `Summary`
- `Problem`
- `Core idea`
- `When to use`
- `When not to use`
- `Implementation notes`
- `Related`

## Workflows

Each workflow is a skill under `.agents/skills/`. Load the skill when its task comes up rather than improvising the procedure:

| Task | Skill | Core rule |
| --- | --- | --- |
| Add a source | `kb-ingest` | Plan first: search for existing notes and prefer extending them over creating near-duplicates. |
| Answer or explore | `kb-query` | `kb.py search` -> `card` -> read 1-4 notes -> `related`; cite notes; flag stale ones. |
| Refresh stale notes | `kb-review` | Write a `reviews/` proposal with checkboxes; change notes only for items the human ticked. |
| Health check | `kb-lint` | `kb.py lint` for mechanics; read a sample for editorial quality. |

Shared rules:

- Make surgical edits to affected pages. Do not rewrite the wiki.
- Never silently overwrite a claim that a new source contradicts. Record both views and set `status: needs-review`.
- Append to `log.md` with `cat >> log.md`. Do not load the whole file. Keep entries to about 10 lines in the `## [YYYY-MM-DD] op | Title` format, and put long reports in `reviews/`.
- Do not read all of `index.md` to find notes; use `python3 .kb/kb.py search`. Edit the index only to add or rename entries.
- Run `python3 .kb/kb.py lint <changed files>` before finishing; it must report zero errors.

## Source Discipline

Raw files in `raw/` are immutable. Do not edit them after ingest. If a source is corrected or superseded, add a new raw source and update generated pages.

When a generated page relies on a raw or external source, list it in frontmatter and in a `Sources` section.

## Wiki vs Project Docs

Use this rule:

- true only for one project or codebase: that project's own `docs/`
- reusable knowledge in this wiki's domain: this repo
- rough task or inbox item: your task tracker or an inbox folder, then promote into the wiki when stable

