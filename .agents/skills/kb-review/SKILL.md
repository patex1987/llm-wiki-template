---
name: kb-review
description: Find knowledge-base notes that are likely outdated, verify them against current primary sources, and write an approval file the user ticks in Obsidian before any note changes. Applies only approved changes. Use when the user asks to refresh, review, or check stale KB notes, or periodically for maintenance.
license: MIT-0
metadata:
  routing-tier: balanced
  routing-effort: medium
---

# KB Review (freshness with approval)

Two phases with a human gate in between. Phase 1 changes no wiki note.

## How staleness is detected

`python3 .kb/kb.py stale` ranks notes by:

- `status: needs-review`
- age against a review interval set by volatility (`.kb/config.json`: high 120 days, medium 270, low 540). Age counts from `reviewed:` (last verified against sources) or, if that is missing, from `updated:`.
- `volatility:` from frontmatter, else inferred from tags in `.kb/config.json`.
- source notes it links to that were updated after it was last reviewed.

The queue is a list of candidates, not a set of findings. A note can be old and still correct.

## Phase 1: verify and propose

1. Pick a batch: the top 3-5 from `kb.py stale`, or the notes the user named. Keep batches small so one proposal is reviewable in a few minutes.
2. For each note, list its checkable claims: versions, defaults, limits, API names, prices, service capabilities, recommendations that depend on tool behaviour. Principles and reasoning rarely need web checks.
3. Check each claim against primary sources first (official docs, changelogs, specs, release notes). Record the URL and the date checked. Note which claims you could not verify.
4. Write `reviews/YYYY-MM-DD-<slug>.md`:

   ```markdown
   ---
   title: "Review YYYY-MM-DD <slug>"
   type: log
   tags: [kb-review]
   status: draft
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   ---

   # Review YYYY-MM-DD <slug>

   Tick the boxes to approve, then ask the agent to apply this review.

   ## [[Note A]]

   Verdict: still accurate | update needed | contradicted | cannot verify

   - [ ] **A1** Mark as verified (sets `reviewed:` to today, no content change)
   - [ ] **A2** Replace "<old claim>" with "<new claim>" in *Implementation notes*
     - Evidence: <url> (checked YYYY-MM-DD): <one-line quote or paraphrase>
   - [ ] **A3** Set `status: deprecated` and point to [[Replacement]]
   ```

   Each item is one independently approvable change, with exact old and new text where it is an edit. Put "still accurate" notes in the same file with a single "mark as verified" item.
5. Stop. Tell the user the file path, the per-note verdicts, and that nothing has been changed yet.

## Phase 2: apply approved items

Run when the user says to apply the review (or ticks boxes and asks).

1. Re-read the review file. Apply only items marked `- [x]`. Unticked items are rejected; leave them alone.
2. If a note changed since the review was written (its `updated:` is newer than the review date), re-check that item before applying it. The old text may be gone.
3. For each applied edit: change the text, set `updated:` and `reviewed:` to today, add the evidence URL to `sources:` and the note's *Sources* section. Store a new raw record under `raw/external-sources/` when the evidence is substantial.
4. `python3 .kb/kb.py lint <changed files>`, which must show zero errors.
5. Set the review file to `status: stable` and append an "Applied" section listing what was applied and what was rejected.
6. Append to `log.md` with `cat >> log.md` (do not read the whole log): `## [YYYY-MM-DD] review | <slug>`, then at most 5 bullets with notes verified, changed, and deprecated, and a link to the review file.

## Rules

- Never change a wiki note in phase 1, and never apply an unticked item.
- A contradiction you cannot resolve becomes `status: needs-review` plus a sentence in the note naming both positions and sources. Do not quietly pick one.
- If version control exists (`git status` works), mention the diff to review after phase 2.
