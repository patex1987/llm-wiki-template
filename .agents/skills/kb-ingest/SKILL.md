---
name: kb-ingest
description: Ingest a new source (URL, pasted text, file, highlight export, chat answer) into this knowledge base - store it under raw/, write a source summary, extend or create concept/pattern/decision notes, then update index.md and log.md. Use when the user says ingest, add to the KB, file this, or drops a source into the vault.
license: MIT-0
metadata:
  routing-tier: balanced
  routing-effort: medium
---

# KB Ingest

Turn one source into durable, linked wiki knowledge. `AGENTS.md` holds the page rules; this skill holds the procedure. The CLI is `python3 .kb/kb.py` from the vault root.

The default failure is near-duplicate pages. **Extend before you create.**

## 1. Capture the raw source

- Pick the folder: `raw/external-sources/` (web articles, docs), `raw/user-provided-documents/` (files the user gave), `raw/copied-chatgpt-answers/` (LLM output), `raw/project-reviews/` (retrospectives and internal reviews).
- File name: `YYYY-MM-DD-kebab-slug.md`. Start it with a short header: origin URL or provenance, capture date, and whether it is primary (official docs, spec, paper), secondary (blog, talk), or LLM-generated.
- If a sync plugin (e.g. Readwise) writes into an inbox folder, treat it as an inbox: copy the relevant items into `raw/` before ingesting and never edit the synced files (the plugin overwrites them).
- Never modify an existing file under `raw/`. A corrected source is a new raw file.

## 2. Plan before writing (cheap step, do not skip)

1. Extract 3-8 candidate claims or ideas worth keeping. Drop anything that is only true for one codebase (that belongs in that project's own docs).
2. For each candidate, find existing coverage:
   `python3 .kb/kb.py search "<idea in plain words>" --limit 5`
   then `python3 .kb/kb.py card "<best hit>"` to see its sections without reading the body.
3. Classify every candidate:
   - **extend**: an existing note covers the topic; add the new mechanism, example, or caveat to the right section.
   - **contradict**: the source disagrees with an existing note. Do not overwrite silently. Record both views in the note with their sources, and set `status: needs-review` if you cannot decide which is right.
   - **new**: no note answers this question. Check `kb.py tags` and reuse existing tags rather than inventing near-duplicates.
   - **skip**: not reusable, or already fully covered.
4. Show the plan to the user as a short table (candidate -> action -> target note) when the source touches more than 3 existing notes or proposes any contradiction. For small ingests, proceed and report afterwards.

## 3. Write

- `sources/<Title>.md`: `type: source`. What the source claims, its evidence quality, and which wiki notes it fed. Link the raw file in `sources:` frontmatter.
- Extended notes: edit only the affected sections. Set `updated:` to today. If you checked the note's existing claims against this source, also set `reviewed:` to today.
- New notes: follow `templates/Note Template.md` and the content rules in `AGENTS.md`. Set `volatility:` (high = fast-moving things such as tool versions, services, prices; medium = practices that shift over years; low = stable principles). `.kb/config.json` can infer it from tags.
- Add `[[wikilinks]]` both ways: a new note links to its neighbours, and at least one existing note links back. `python3 .kb/kb.py related "<new note>"` lists shared-tag notes that are not linked yet.
- Keep source claims, KB synthesis, and your own examples clearly distinguished in the text.

## 4. Verify and record

1. `python3 .kb/kb.py lint <every file you created or changed>` must report zero errors. Fix warnings for files you touched.
2. Read the finished notes once as a reader would. A note that has every heading but does not explain the mechanism has not passed.
3. Add new pages to `index.md` without loading the whole file: `rg -n '^## ' index.md` gives the section line numbers (without ripgrep: `grep -n '^## ' index.md`). Read only a few lines of the target section and insert one line: `- [[Note]] - <one-line description>`.
4. Append a log entry with the shell, without reading `log.md` (it is large, and only its tail matters):

   ```bash
   cat >> log.md <<'EOF'

   ## [YYYY-MM-DD] ingest | <Source title>

   - Raw: raw/...
   - Created: [[...]]
   - Extended: [[...]] (what changed)
   - Contradictions: none | [[...]] (marked needs-review)
   EOF
   ```

   Keep entries to about 10 lines. The log records what happened. Put analysis, audit tables, and verification detail in the source note or a `reviews/` file and link to it.

## Batch ingest

For several sources, run step 2 for all of them first and merge the plans, so two sources do not create two notes on the same topic. Then write one source at a time. Stop and ask after the plan if the batch would create more than 5 new notes.

## Report to the user

List created and extended notes, any contradictions flagged, and the lint result. Do not paste note bodies.
