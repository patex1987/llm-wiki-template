# LLM Wiki Template

A starter repo for a **personal or team knowledge base that an LLM agent writes and maintains**, following the "LLM Wiki" pattern described by Andrej Karpathy. Clone it, point Claude Code (or Codex, OpenCode, ...) at it, and start feeding it sources.

It is plain Markdown plus a small stdlib-only Python CLI. It works well as an [Obsidian](https://obsidian.md) vault, but Obsidian is optional.

> **Heads-up: this approach may not scale, and the field is moving fast.** See [Limits and open questions](#limits-and-open-questions-read-this-before-betting-on-it) before building a lot on it.

## The idea in one minute

Most "chat with your documents" tools work like RAG: at question time they retrieve chunks and synthesize an answer from scratch. Nothing accumulates. The LLM Wiki flips that:

> Instead of just retrieving from raw documents at query time, the LLM **incrementally builds and maintains a persistent wiki** — a structured, interlinked collection of markdown files that sits between you and the raw sources.
>
> — Karpathy, [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

> The wiki is a persistent, compounding artifact. The cross-references are already there. The contradictions have already been flagged.

> The tedious part of maintaining a knowledge base is not the reading or the thinking — it's the bookkeeping.

You curate sources and ask questions. The agent does the summarizing, cross-referencing, filing and consistency checks that humans abandon wikis over.

### Three layers

| Layer | What | Who changes it |
| --- | --- | --- |
| **Raw sources** (`raw/`) | Articles, papers, chat exports, notes. Immutable source of truth. | You add; nobody edits |
| **The wiki** (`concepts/`, `patterns/`, `decisions/`, `snippets/`, `sources/`) | LLM-written, interlinked notes with frontmatter | The agent |
| **The schema** (`AGENTS.md`, `.agents/skills/`) | Rules and procedures that make the agent a disciplined maintainer rather than a chatbot | You and the agent, together |

### Three operations

- **Ingest**: drop in a source; the agent stores it under `raw/`, writes a summary, extends or creates topic notes, updates `index.md`, appends to `log.md`. One source can touch 10-15 pages.
- **Query**: ask a question; the agent searches, reads a few notes, answers with citations. Good answers can be filed back as new notes so explorations compound too.
- **Lint**: periodic health check for broken links, orphans, contradictions, stale claims and missing pages.

### Two navigation files

- `index.md`: content catalog, one line per note.
- `log.md`: append-only chronology with greppable headings (`## [2026-11-13] ingest | Title`).

## How this template implements it

Karpathy's document is intentionally abstract ("it describes the idea, not a specific implementation"). This repo is one concrete, battle-tested instantiation, extracted from a real programming knowledge base of roughly 275 notes.

| Piece | File | Role |
| --- | --- | --- |
| Schema | [`AGENTS.md`](AGENTS.md) (`CLAUDE.md` imports it) | Page format, linking rules, content-quality bar, shared rules |
| Ingest skill | [`.agents/skills/kb-ingest`](.agents/skills/kb-ingest/SKILL.md) | Capture raw, plan (extend before create), write, lint, index, log |
| Query skill | [`.agents/skills/kb-query`](.agents/skills/kb-query/SKILL.md) | Search -> card -> read 1-4 notes -> related; cite; flag stale notes |
| Lint skill | [`.agents/skills/kb-lint`](.agents/skills/kb-lint/SKILL.md) | Mechanical checks plus a sampled editorial pass |
| Review skill | [`.agents/skills/kb-review`](.agents/skills/kb-review/SKILL.md) | Verify stale notes against primary sources; write a checkbox proposal; apply only what you tick |
| CLI | [`.kb/kb.py`](.kb/kb.py) | `search` (BM25), `card`, `related`, `tags`, `stale`, `lint`, `eval`, `log` |
| Config | [`.kb/config.json`](.kb/config.json) | Review intervals, volatility-by-tag, and optional schema overrides |

Skills live in `.agents/skills/` and are linked into `.claude/skills` so Claude Code finds them; other agents can read the same files.

Design choices that go beyond the original note:

- **Human gate for freshness.** `kb-review` never edits notes directly; it writes a `reviews/` file with checkboxes and only applies ticked items.
- **Provenance discipline.** Source claims, synthesis, hypothetical examples and verified behavior are kept distinct; contradictions are recorded, not silently overwritten.
- **Cheap retrieval.** `kb.py` ranks notes so the agent rarely reads the whole index; the log is append-only via `cat >>` and never loaded in full.

## Quick start

```bash
# 1. Use this repo as a template (GitHub: "Use this template"), or clone it
git clone https://github.com/patex1987/llm-wiki-template my-wiki
cd my-wiki

# 2. Check the tooling works (should print 0 errors)
python3 .kb/kb.py lint

# 3. Open the folder in Claude Code (or another agent) and, optionally, in Obsidian
claude
```

Then:

1. **Tailor the schema.** Tell the agent your domain and have it edit the Purpose section of `AGENTS.md` (and, if needed, the directories, page types and required sections; see [Adapting to your domain](#adapting-to-your-domain)).
2. **Ingest your first source:** "Ingest this: <url or pasted text>" (triggers `kb-ingest`).
3. **Ask a question:** "What does the KB say about X?" (triggers `kb-query`).
4. **Maintain:** "Run a lint" / "Check which notes are stale" (`kb-lint`, `kb-review`).

The seed notes (`[[LLM Wiki]]`, `[[Karpathy LLM Wiki]]`) show the expected note shape. Delete them once you have your own content, and remove their entries from `index.md` and `log.md`.

## Layout

```text
AGENTS.md            the schema (CLAUDE.md just imports it)
index.md             content catalog
log.md               chronological maintenance log
concepts/            explanations and mental models
patterns/            procedures and recipes
decisions/           decisions with rationale
snippets/            templates and small worked examples
sources/             generated summaries of ingested sources
raw/                 immutable inputs (external-sources, user-provided-documents,
                     copied-chatgpt-answers, project-reviews)
reviews/             freshness-review proposals awaiting your approval
templates/           note template
.agents/skills/      workflow skills (.claude/skills links here)
.kb/                 kb.py, config.json, eval/queries.jsonl
```

## CLI cheat sheet

```bash
python3 .kb/kb.py search "your question" [--tag t] [--type concept] [--limit 5]
python3 .kb/kb.py card "Note Title"        # metadata + section names, no body
python3 .kb/kb.py related "Note Title"     # links, backlinks, shared-tag neighbours
python3 .kb/kb.py tags --similar           # tag hygiene
python3 .kb/kb.py stale --limit 20         # freshness queue
python3 .kb/kb.py lint [PATH ...]          # must report zero errors
python3 .kb/kb.py eval .kb/eval/queries.jsonl   # retrieval regression check
python3 .kb/kb.py log --last 10
```

Add `--json` to `search`, `card`, `related` and `stale` for machine-readable output.

## Adapting to your domain

The directory names and sections are a programming-flavoured default, not part of the pattern. To change them:

- `.kb/config.json` accepts optional `wiki_dirs`, `allowed_types`, `allowed_status`, `required_sections` and `sectioned_types` keys (defaults are in `kb.py`). Example for a book-companion wiki:

  ```json
  {
    "wiki_dirs": ["characters", "themes", "chapters", "sources"],
    "allowed_types": ["character", "theme", "chapter", "source", "index", "log", "template"],
    "required_sections": ["Summary", "Related"],
    "sectioned_types": ["character", "theme"]
  }
  ```

- Update the layout and page rules in `AGENTS.md` and the folder names mentioned in the skills to match.
- Replace the `high_tags` / `low_tags` lists in `config.json` with tags that go stale fast or slowly in your domain.
- Replace `.kb/eval/queries.jsonl` with real questions and the notes that should answer them.

## Limits and open questions (read this before betting on it)

**We will need to explore other solutions.** This pattern is a good start, and it may not scale well. The tooling and the industry are changing quickly (agent memory, long-context models, graph and hybrid retrieval, MCP-served knowledge, vendor-built "memory" features), so treat this repo as a snapshot of one workable approach, not an endpoint.

What the original author says (source claims):

> [index.md] works surprisingly well at moderate scale (~100 sources, ~hundreds of pages) and avoids the need for embedding-based RAG infrastructure.

> At some point you may want to build small tools that help the LLM operate on the wiki more efficiently. A search engine over the wiki pages is the most obvious one ... [qmd](https://github.com/tobi/qmd) is a good option.

> This document is intentionally abstract. It describes the idea, not a specific implementation.

So the source itself places the comfortable range at roughly a hundred sources and a few hundred pages, and points to search tooling beyond that.

What we have seen in practice and what we suspect (our observations and inference, not source claims):

- **Observed:** in the knowledge base this template was extracted from (about 275 notes), `index.md` had grown to roughly 43 KB (around 11k tokens) and `log.md` to roughly 84 KB. Reading either in full per task is wasteful, which is why `kb.py search` and tail-only log appends exist. They delay the problem; they do not remove it.
- **Suspected:** ingest cost grows with the wiki, because "extend before you create" needs a search and several reads per source, and a source can touch many pages.
- **Suspected:** errors compound. An LLM-written claim that nobody checks becomes the input for later synthesis. The `reviewed`/`volatility` fields, `kb-review` and the source-vs-synthesis rule mitigate this but rely on human attention that does not scale with note count.
- **Suspected:** multi-author use is awkward. Several people (or agents) editing the same interlinked pages invites merge conflicts and contradictory edits; git helps but does not resolve semantic conflicts.
- **Suspected:** a hand-rolled BM25 search is a stopgap. Hybrid or vector search, a graph store, or serving the wiki over MCP might serve larger corpora better.
- **Open:** whether bigger context windows and built-in agent memory make a hand-maintained wiki less necessary, or make a well-structured one more valuable.

Things worth trying when you hit the wall: a proper local search engine such as [qmd](https://github.com/tobi/qmd), sharding into several smaller wikis per domain, an index split into per-section files, a retrieval eval that you actually track (`kb.py eval`), and comparing against plain RAG or an agent-memory product on your own questions.

## Credits and license

- The pattern is from Andrej Karpathy's [LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Short excerpts above are quoted for explanation; read the original for the full text. This repo is an independent implementation and is not affiliated with or endorsed by the author.
- Code and templates: [MIT](LICENSE).
