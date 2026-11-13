---
name: kb-lint
description: Run a structural and editorial health check of this knowledge base - broken links, frontmatter, missing sections, orphans, index coverage, near-duplicate tags, merge/split candidates, and concepts that deserve their own page - and fix mechanical issues with the user's approval. Use when the user asks for lint, cleanup, KB health, or tag hygiene.
license: MIT-0
metadata:
  routing-tier: fast
  routing-effort: low
---

# KB Lint

Mechanical checks come from the CLI; judgement calls come from reading. Freshness is a separate skill (`kb-review`).

## 1. Mechanical pass

`python3 .kb/kb.py lint` checks frontmatter fields and allowed values, date formats, required concept/pattern sections, unresolved wikilinks and `related`/`sources` entries, unbalanced code fences, orphans, `index.md` coverage, near-duplicate tags, loose root files, and log ordering. It exits non-zero on errors.

Group findings for the user:

- **Safe to auto-fix** (propose as one batch, apply on a yes): missing index entries, an obvious link-target typo when exactly one note matches, singular/plural tag duplicates (rename the rarer tag to the common one across all notes), adding a backlink to an orphan from its most related note (`kb.py related`).
- **Needs a decision**: broken links whose target was never written (create the page, or remove the link?), loose root files and inbox items (ingest, move to `raw/`, or delete?), and missing required sections (expand, or is the note really a source or decision?).

Never delete user files or anything under `raw/` without explicit approval.

## 2. Editorial pass (sampled)

Pick 5-10 notes: recently changed ones (`kb.py lint --changed-since <date>` lists them), plus a few random older ones. For each, ask:

- Does it explain the mechanism and its assumptions, or just restate headings?
- Is it a near duplicate of another note? Compare with `kb.py related`, then propose merging or sharpening the scopes.
- Is it doing two jobs? Propose a split.
- Does the body mention a concept that recurs across notes but has no page? (`rg -c "<term>"` across notes indicates recurrence.)

## 3. Record

Append `## [YYYY-MM-DD] lint | <scope>` to `log.md` with `cat >> log.md` (do not read the whole log): counts from `kb.py lint`, fixes applied, open decisions, in at most 8 bullets. A long editorial audit goes in its own `reviews/YYYY-MM-DD-lint.md` file, linked from the entry.
