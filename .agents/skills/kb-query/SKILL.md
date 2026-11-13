---
name: kb-query
description: Answer a question from this knowledge base with targeted retrieval (ranked search, note cards, link graph) and cited notes; optionally file a reusable answer back into the wiki. Use when the user asks what the KB says, asks a question the KB likely covers, or wants to explore tags and relationships between notes.
license: MIT-0
metadata:
  routing-tier: fast
  routing-effort: low
---

# KB Query

Load the fewest notes that answer the question. The CLI is `python3 .kb/kb.py` from the vault root; it ranks notes by field-weighted BM25 over title, aliases, tags, summary, and body, and prints a one-line summary per hit, so you rarely need to open `index.md` (it is about 11k tokens).

## Retrieval ladder

Stop at the first rung that gives enough evidence.

1. **Search**: `kb.py search "<question in plain words>"`. Narrow with `--tag`, `--type pattern|concept|decision|source`, or `--status stable`. Try 2-3 phrasings with synonyms if the first misses (e.g. a term and its common synonym).
2. **Card**: `kb.py card "<note>"` shows metadata, summary, section names, and sources without the body. Use it to choose between near hits.
3. **Read**: open the 1-4 best notes in full. Prefer `status: stable`. Treat `needs-review` and `draft` as leads, not authority.
4. **Expand**: `kb.py related "<note>"` shows links, backlinks, two-hop neighbours, and notes that share tags but are not linked. Open a neighbour only if the question needs it (comparison, prerequisite, trade-off).
5. **Fallback**: `rg -n -i "<exact term>" concepts patterns decisions sources` for exact identifiers, config keys, or error strings that search tokenization may split.

For exploration requests ("what do I have on authorization?", "how do these relate?"), use `kb.py tags`, `kb.py search --tag <tag>`, and `kb.py related` and present the cluster as a short map: hub notes, how they relate, and gaps.

## Answer

- Synthesize for the user's situation; do not dump notes.
- End with `Used KB notes: [[A]], [[B]]`.
- Keep "the KB says" separate from anything you add from general knowledge.
- If a note you used is `needs-review`, has `volatility: high` with a `reviewed`/`updated` date older than about 4 months, or conflicts with another note, say so in one line: `KB freshness note: [[X]] may be stale because <reason>.` Offer to run the `kb-review` skill on it.
- If the KB has no useful note, say so plainly.

## Filing answers back

If the answer is a reusable synthesis (a comparison, decision, or worked example that no note has), offer to file it. On a yes, follow the write and verify steps of the `kb-ingest` skill with the conversation as the source (`raw/copied-chatgpt-answers/` is the right raw folder for model-generated synthesis). Log it as `## [YYYY-MM-DD] query | <question>` by appending with `cat >> log.md`.
