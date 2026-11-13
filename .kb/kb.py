#!/usr/bin/env python3
"""LLM wiki helper: search, graph navigation, freshness, and lint.

Standard library only. Every command reads the Markdown files directly, so there
is no index to rebuild. Run from anywhere:

    python3 .kb/kb.py search "your query"
    python3 .kb/kb.py card "LLM Wiki"
    python3 .kb/kb.py related "LLM Wiki"
    python3 .kb/kb.py tags [--similar]
    python3 .kb/kb.py stale [--limit 20]
    python3 .kb/kb.py lint [--changed-since YYYY-MM-DD] [PATH ...]
    python3 .kb/kb.py eval .kb/eval/queries.jsonl [--k 5]
    python3 .kb/kb.py log [--last 10]

Add --json to search, card, related, and stale for machine-readable output.
The command set maps one-to-one onto MCP tools if the KB is ever served over MCP.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / ".kb" / "config.json"
WIKI_DIRS = ("concepts", "patterns", "decisions", "snippets", "sources")
REQUIRED_FIELDS = ("title", "type", "tags", "status", "created", "updated")
ALLOWED_TYPES = {"concept", "pattern", "decision", "snippet", "source", "index", "log", "template"}
ALLOWED_STATUS = {"draft", "stable", "needs-review", "deprecated"}
REQUIRED_SECTIONS = ("Summary", "Problem", "Core idea", "When to use", "When not to use",
                     "Implementation notes", "Related")
FIELD_WEIGHTS = {"title": 5.0, "aliases": 4.0, "tags": 3.0, "summary": 2.0, "body": 1.0}

WIKILINK_RE = re.compile(r"!?\[\[([^\]]+?)\]\]")
WORD_RE = re.compile(r"[a-z0-9]+(?:[.+#][a-z0-9]+)*")
FM_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.S)
CODE_RE = re.compile(r"```.*?```|`[^`\n]*`", re.S)


# --------------------------------------------------------------------------- parsing

def _scalar(value: str):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse the flat YAML subset used by this vault (scalars and string lists)."""
    m = FM_RE.match(text)
    if not m:
        return {}, text
    data: dict = {}
    key = None
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s*-\s+(.*)$", line)
        if item and key is not None:
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(_scalar(item.group(1)))
            continue
        kv = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not kv:
            continue
        key, raw = kv.group(1), kv.group(2).strip()
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            data[key] = [_scalar(x) for x in inner.split(",")] if inner else []
        elif raw == "":
            data[key] = []
        else:
            data[key] = _scalar(raw)
    return data, text[m.end():]


def parse_date(value) -> dt.date | None:
    if not isinstance(value, str):
        return None
    try:
        return dt.date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def sections(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in body.splitlines():
        h = re.match(r"^##\s+(.+?)\s*$", line)
        if h:
            if current:
                out[current] = "\n".join(buf).strip()
            current, buf = h.group(1), []
        elif current:
            buf.append(line)
    if current:
        out[current] = "\n".join(buf).strip()
    return out


def tokenize(text: str) -> list[str]:
    toks = WORD_RE.findall(text.lower())
    return [t[:-1] if len(t) > 4 and t.endswith("s") and not t.endswith("ss") else t for t in toks]


def link_target(raw: str) -> str:
    target = raw.split("|", 1)[0].split("#", 1)[0].strip().rstrip("\\").strip()
    return target[:-3] if target.endswith(".md") else target


@dataclass
class Note:
    path: Path
    rel: str
    name: str
    fm: dict
    body: str
    links: list[str] = field(default_factory=list)

    @property
    def tags(self) -> list[str]:
        t = self.fm.get("tags") or []
        return [x for x in t if x] if isinstance(t, list) else [t]

    @property
    def aliases(self) -> list[str]:
        a = self.fm.get("aliases") or []
        return a if isinstance(a, list) else [a]

    @property
    def summary(self) -> str:
        s = sections(self.body).get("Summary", "")
        if not s:
            paras = [p for p in self.body.split("\n\n") if p.strip() and not p.lstrip().startswith("#")]
            s = paras[0] if paras else ""
        s = " ".join(s.split())
        m = re.match(r"(.{40,}?[.!?])\s", s + " ")
        return (m.group(1) if m else s)[:300]


class Vault:
    def __init__(self, root: Path = ROOT):
        self.root = root
        self.config = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
        self.notes: dict[str, Note] = {}
        self.files_by_stem: dict[str, list[str]] = defaultdict(list)
        self.all_rel: set[str] = set()
        for p in root.rglob("*"):
            rel = p.relative_to(root).as_posix()
            if p.is_dir() or rel.split("/")[0].startswith("."):
                continue
            self.all_rel.add(rel)
            stem = p.stem if p.suffix == ".md" else p.name
            self.files_by_stem[stem.lower()].append(rel)
        self.wiki_dirs = tuple(self.config.get("wiki_dirs", WIKI_DIRS))
        for d in self.wiki_dirs:
            for p in sorted((root / d).glob("*.md")):
                text = p.read_text(encoding="utf-8", errors="replace")
                fm, body = parse_frontmatter(text)
                note = Note(p, p.relative_to(root).as_posix(), p.stem, fm, body)
                note.links = [link_target(x) for x in WIKILINK_RE.findall(CODE_RE.sub("", text))]
                self.notes[note.name.lower()] = note

    def resolve(self, target: str) -> str | None:
        """Resolve a wikilink or path the way Obsidian does: by path, else by file name."""
        t = target.strip().rstrip("/")
        if not t:
            return None
        for cand in (t, t + ".md"):
            if cand in self.all_rel:
                return cand
        hits = self.files_by_stem.get(Path(t).name.lower()) or self.files_by_stem.get(t.lower())
        return hits[0] if hits else None

    def find(self, query: str) -> Note | None:
        q = link_target(query).lower()
        q = Path(q).name if "/" in q else q
        if q in self.notes:
            return self.notes[q]
        for n in self.notes.values():
            if q in (a.lower() for a in n.aliases):
                return n
        best = search(self, query, limit=1)
        return best[0][1] if best else None

    def note_for_rel(self, rel: str | None) -> Note | None:
        if not rel or not rel.endswith(".md"):
            return None
        return self.notes.get(Path(rel).stem.lower())


# --------------------------------------------------------------------------- search

def search(vault: Vault, query: str, limit: int = 10, tag: str | None = None,
           ntype: str | None = None, status: str | None = None) -> list[tuple[float, Note]]:
    """Field-weighted BM25 over title, aliases, tags, summary, and body."""
    qtoks = tokenize(query.replace("-", " "))
    if not qtoks:
        return []
    docs = []
    for n in vault.notes.values():
        if tag and tag not in n.tags:
            continue
        if ntype and n.fm.get("type") != ntype:
            continue
        if status and n.fm.get("status") != status:
            continue
        fields = {
            "title": tokenize(n.fm.get("title") or n.name),
            "aliases": tokenize(" ".join(n.aliases)),
            "tags": tokenize(" ".join(t.replace("-", " ") for t in n.tags)),
            "summary": tokenize(n.summary),
            "body": tokenize(n.body),
        }
        docs.append((n, fields))
    if not docs:
        return []
    N = len(docs)
    df = Counter()
    for _, f in docs:
        df.update(set(f["body"]) | set(f["title"]) | set(f["aliases"]) | set(f["tags"]))
    avg_len = {k: (sum(len(f[k]) for _, f in docs) / N) or 1.0 for k in FIELD_WEIGHTS}
    k1, b = 1.2, 0.75
    phrase = query.lower().strip()
    scored = []
    for n, f in docs:
        score = 0.0
        for q in set(qtoks):
            idf = math.log(1 + (N - df[q] + 0.5) / (df[q] + 0.5))
            for fname, w in FIELD_WEIGHTS.items():
                tf = f[fname].count(q)
                if tf:
                    norm = tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(f[fname]) / avg_len[fname]))
                    score += w * idf * norm
        title = (n.fm.get("title") or n.name).lower()
        if phrase == title or phrase in (a.lower() for a in n.aliases):
            score += 25
        elif len(phrase) > 3 and phrase in title:
            score += 8
        if n.fm.get("status") == "stable":
            score *= 1.1
        elif n.fm.get("status") == "deprecated":
            score *= 0.5
        if score > 0:
            scored.append((score, n))
    scored.sort(key=lambda x: -x[0])
    return scored[:limit]


# --------------------------------------------------------------------------- graph

def graph(vault: Vault):
    out_links: dict[str, set[str]] = defaultdict(set)
    in_links: dict[str, set[str]] = defaultdict(set)
    for n in vault.notes.values():
        targets = list(n.links)
        rel = n.fm.get("related") or []
        targets += rel if isinstance(rel, list) else [rel]
        for t in targets:
            other = vault.note_for_rel(vault.resolve(link_target(t)))
            if other and other is not n:
                out_links[n.name].add(other.name)
                in_links[other.name].add(n.name)
    return out_links, in_links


def related(vault: Vault, note: Note, limit: int = 8) -> dict:
    out_links, in_links = graph(vault)
    mine = set(note.tags)
    neighbours = []
    for other in vault.notes.values():
        if other is note or not mine:
            continue
        shared = mine & set(other.tags)
        if shared:
            j = len(shared) / len(mine | set(other.tags))
            neighbours.append((round(j, 2), other.name, sorted(shared)))
    neighbours.sort(key=lambda x: -x[0])
    linked = out_links[note.name] | in_links[note.name]
    two_hop = Counter()
    for n1 in linked:
        for n2 in out_links[n1] | in_links[n1]:
            if n2 != note.name and n2 not in linked:
                two_hop[n2] += 1
    return {
        "note": note.name,
        "path": note.rel,
        "links_to": sorted(out_links[note.name]),
        "linked_from": sorted(in_links[note.name]),
        "shared_tags_not_linked": [
            {"note": n, "jaccard": j, "shared": s} for j, n, s in neighbours if n not in linked
        ][:limit],
        "two_hop": [{"note": n, "paths": c} for n, c in two_hop.most_common(limit)],
    }


# --------------------------------------------------------------------------- freshness

def volatility(vault: Vault, note: Note) -> str:
    v = note.fm.get("volatility")
    if v in ("high", "medium", "low"):
        return v
    cfg = vault.config.get("volatility", {})
    tags = set(note.tags)
    if tags & set(cfg.get("high_tags", [])):
        return "high"
    if note.fm.get("type") in cfg.get("low_types", []) or tags & set(cfg.get("low_tags", [])):
        return "low"
    return "medium"


def freshness(vault: Vault, today: dt.date) -> list[dict]:
    intervals = vault.config.get("review_interval_days", {"high": 120, "medium": 270, "low": 540})
    out_links, _ = graph(vault)
    rows = []
    for n in vault.notes.values():
        if n.fm.get("type") in ("index", "log", "template"):
            continue
        status = n.fm.get("status")
        if status == "deprecated":
            continue
        reviewed = parse_date(n.fm.get("reviewed"))
        basis = reviewed or parse_date(n.fm.get("updated")) or parse_date(n.fm.get("created"))
        if not basis:
            rows.append({"note": n.name, "path": n.rel, "score": 99, "reasons": ["no usable date"]})
            continue
        vol = volatility(vault, n)
        age = (today - basis).days
        due_in = intervals[vol] - age
        reasons, score = [], 0.0
        if status == "needs-review":
            reasons.append("status: needs-review")
            score += 50
        if due_in <= 0:
            reasons.append(f"{vol} volatility, {age}d since {'reviewed' if reviewed else 'updated'}")
            score += 20 + min(-due_in, 365) / 10
        newer = []
        for other_name in out_links[n.name]:
            other = vault.notes.get(other_name.lower())
            ou = parse_date(other.fm.get("updated")) if other else None
            if other and ou and ou > basis and other.fm.get("type") == "source":
                newer.append(other.name)
        if newer:
            reasons.append("linked sources changed since: " + ", ".join(sorted(newer)[:3]))
            score += 5 * len(newer)
        if reasons:
            rows.append({"note": n.name, "path": n.rel, "score": round(score, 1), "volatility": vol,
                         "basis": basis.isoformat(), "reviewed": bool(reviewed),
                         "due_in_days": due_in, "reasons": reasons})
    rows.sort(key=lambda r: -r["score"])
    return rows


# --------------------------------------------------------------------------- lint

def similar_tags(counts: Counter) -> list[tuple[str, str]]:
    def norm(t: str) -> str:
        t = t.lower().replace("_", "-")
        t = re.sub(r"(ies)$", "y", t)
        return re.sub(r"(?<!s)s$", "", t).replace("-", "")
    groups = defaultdict(list)
    for t in counts:
        groups[norm(t)].append(t)
    return [tuple(sorted(g)) for g in groups.values() if len(g) > 1]


def lint(vault: Vault, paths: list[str] | None, changed_since: dt.date | None) -> list[tuple[str, str, str]]:
    issues: list[tuple[str, str, str]] = []
    selected = list(vault.notes.values())
    if paths:
        wanted = {Path(p).resolve() for p in paths}
        selected = [n for n in selected if n.path.resolve() in wanted]
    if changed_since:
        selected = [n for n in selected if (parse_date(n.fm.get("updated")) or dt.date.min) >= changed_since]
    _, in_links = graph(vault)
    allowed_types = set(vault.config.get("allowed_types", ALLOWED_TYPES))
    allowed_status = set(vault.config.get("allowed_status", ALLOWED_STATUS))
    required_sections = tuple(vault.config.get("required_sections", REQUIRED_SECTIONS))
    section_types = tuple(vault.config.get("sectioned_types", ("concept", "pattern")))
    index_text = (vault.root / "index.md").read_text() if (vault.root / "index.md").exists() else ""
    indexed = {link_target(x).lower() for x in WIKILINK_RE.findall(index_text)}
    indexed = {Path(x).name for x in indexed}
    for n in selected:
        fm = n.fm
        if not fm:
            issues.append(("error", n.rel, "missing frontmatter"))
            continue
        for k in REQUIRED_FIELDS:
            if k not in fm or fm[k] in ("", None):
                issues.append(("error", n.rel, f"missing frontmatter field: {k}"))
        if fm.get("type") and fm["type"] not in allowed_types:
            issues.append(("error", n.rel, f"unknown type: {fm['type']}"))
        if fm.get("status") and fm["status"] not in allowed_status:
            issues.append(("error", n.rel, f"unknown status: {fm['status']}"))
        for k in ("created", "updated", "reviewed"):
            if k in fm and not parse_date(fm[k]):
                issues.append(("error", n.rel, f"unparseable date in {k}: {fm[k]!r}"))
        if fm.get("volatility") and fm["volatility"] not in ("high", "medium", "low"):
            issues.append(("error", n.rel, f"volatility must be high|medium|low: {fm['volatility']}"))
        if fm.get("type") in section_types:
            have = set(sections(n.body))
            missing = [s for s in required_sections if s not in have]
            if missing:
                issues.append(("warn", n.rel, "missing sections: " + ", ".join(missing)))
        for t in set(n.links):
            if t and not vault.resolve(t):
                issues.append(("error", n.rel, f"unresolved link: [[{t}]]"))
        for k in ("related", "sources"):
            vals = fm.get(k) or []
            for v in vals if isinstance(vals, list) else [vals]:
                if v and not re.match(r"^[a-z]+://", v) and not vault.resolve(link_target(v)):
                    issues.append(("error", n.rel, f"{k} entry does not resolve: {v}"))
        if n.body.count("```") % 2:
            issues.append(("warn", n.rel, "unbalanced code fence"))
        if n.name not in in_links:
            issues.append(("warn", n.rel, "orphan: no inbound links"))
        if n.name.lower() not in indexed:
            issues.append(("warn", n.rel, "not listed in index.md"))
    if not paths and not changed_since:
        counts = Counter(t for n in vault.notes.values() for t in n.tags)
        for group in similar_tags(counts):
            issues.append(("warn", "tags", "near-duplicate tags: " + ", ".join(
                f"{t} ({counts[t]})" for t in group)))
        known = {"AGENTS.md", "CLAUDE.md", "README.md", "index.md", "log.md", "LICENSE"}
        for rel in sorted(vault.all_rel):
            if "/" not in rel and rel not in known:
                issues.append(("info", rel, "loose file in vault root (inbox item?)"))
        dates = [parse_date(m) for m in re.findall(r"^## \[(\d{4}-\d{2}-\d{2})\]",
                                                   (vault.root / "log.md").read_text(), re.M)]
        if any(a and b and b < a for a, b in zip(dates, dates[1:])):
            issues.append(("warn", "log.md", "entries are not in chronological order"))
    return issues


# --------------------------------------------------------------------------- cli

def card(vault: Vault, n: Note) -> dict:
    return {
        "note": n.name, "path": n.rel, "type": n.fm.get("type"), "status": n.fm.get("status"),
        "updated": n.fm.get("updated"), "reviewed": n.fm.get("reviewed"),
        "volatility": volatility(vault, n), "tags": n.tags, "aliases": n.aliases,
        "summary": n.summary, "sections": list(sections(n.body)),
        "sources": n.fm.get("sources") or [],
    }


def emit(data, as_json: bool, render) -> None:
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        render(data)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="ranked search with one-line summaries")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=8)
    s.add_argument("--tag")
    s.add_argument("--type")
    s.add_argument("--status")
    s.add_argument("--json", action="store_true")
    c = sub.add_parser("card", help="metadata and summary of one note, without the body")
    c.add_argument("note")
    c.add_argument("--json", action="store_true")
    r = sub.add_parser("related", help="links, backlinks, two-hop and shared-tag neighbours")
    r.add_argument("note")
    r.add_argument("--limit", type=int, default=8)
    r.add_argument("--json", action="store_true")
    t = sub.add_parser("tags", help="tag counts")
    t.add_argument("--min", type=int, default=1)
    t.add_argument("--similar", action="store_true", help="only near-duplicate tag groups")
    st = sub.add_parser("stale", help="review queue ranked by freshness risk")
    st.add_argument("--limit", type=int, default=20)
    st.add_argument("--today", help="override today's date (YYYY-MM-DD)")
    st.add_argument("--json", action="store_true")
    li = sub.add_parser("lint", help="structural checks")
    li.add_argument("paths", nargs="*")
    li.add_argument("--changed-since")
    li.add_argument("--level", choices=("error", "warn", "info"), default="info")
    ev = sub.add_parser("eval", help="recall@k of search over a JSONL file of {query, expect}")
    ev.add_argument("file")
    ev.add_argument("--k", type=int, default=5)
    lg = sub.add_parser("log", help="last log entries")
    lg.add_argument("--last", type=int, default=10)
    a = ap.parse_args(argv)

    vault = Vault()

    if a.cmd == "search":
        res = search(vault, a.query, a.limit, a.tag, a.type, a.status)
        data = [{"score": round(sc, 1), **card(vault, n)} for sc, n in res]
        emit(data, a.json, lambda d: [print(
            f"{x['score']:6.1f}  {x['path']}  [{x['status']}, {x['updated']}]\n        {x['summary']}")
            for x in d] or print("no matches"))
    elif a.cmd == "card":
        n = vault.find(a.note)
        if not n:
            print(f"no note matches {a.note!r}", file=sys.stderr)
            return 1
        emit(card(vault, n), a.json, lambda d: print("\n".join(
            f"{k}: {', '.join(v) if isinstance(v, list) else v}" for k, v in d.items())))
    elif a.cmd == "related":
        n = vault.find(a.note)
        if not n:
            print(f"no note matches {a.note!r}", file=sys.stderr)
            return 1
        def show(d):
            print(f"{d['note']}  ({d['path']})")
            print("  links to:     " + "; ".join(d["links_to"]))
            print("  linked from:  " + "; ".join(d["linked_from"]))
            print("  two hops:     " + "; ".join(f"{x['note']} (x{x['paths']})" for x in d["two_hop"]))
            print("  shared tags, not linked (link candidates):")
            for x in d["shared_tags_not_linked"]:
                print(f"    {x['jaccard']:.2f}  {x['note']}  [{', '.join(x['shared'])}]")
        emit(related(vault, n, a.limit), a.json, show)
    elif a.cmd == "tags":
        counts = Counter(t for n in vault.notes.values() for t in n.tags)
        if a.similar:
            for g in similar_tags(counts):
                print(", ".join(f"{t} ({counts[t]})" for t in g))
        else:
            for tag_name, cnt in counts.most_common():
                if cnt >= a.min:
                    print(f"{cnt:4d}  {tag_name}")
    elif a.cmd == "stale":
        today = (parse_date(a.today) if a.today else None) or dt.date.today()
        rows = freshness(vault, today)[: a.limit]
        emit(rows, a.json, lambda d: [print(
            f"{x['score']:5.1f}  {x['path']}\n       " + "; ".join(x["reasons"])) for x in d]
            or print("nothing due"))
    elif a.cmd == "lint":
        since = parse_date(a.changed_since) if a.changed_since else None
        order = {"error": 0, "warn": 1, "info": 2}
        issues = [i for i in lint(vault, a.paths, since) if order[i[0]] <= order[a.level]]
        for level, where, msg in sorted(issues, key=lambda i: (order[i[0]], i[1])):
            print(f"{level:5s}  {where}: {msg}")
        summary = Counter(i[0] for i in issues)
        print(f"\n{summary['error']} errors, {summary['warn']} warnings, {summary['info']} info")
        return 1 if summary["error"] else 0
    elif a.cmd == "eval":
        cases = [json.loads(x) for x in Path(a.file).read_text().splitlines() if x.strip()]
        hits = 0
        for case in cases:
            got = [n.name.lower() for _, n in search(vault, case["query"], a.k)]
            want = [w.lower() for w in case["expect"]]
            ok = any(w in got for w in want)
            hits += ok
            if not ok:
                print(f"MISS  {case['query']!r}\n      want {case['expect']}, got {got[:3]}")
        print(f"recall@{a.k}: {hits}/{len(cases)} = {hits / max(len(cases), 1):.2f}")
        return 0 if cases and hits == len(cases) else 1
    elif a.cmd == "log":
        text = (vault.root / "log.md").read_text()
        entries = re.split(r"(?m)^(?=## \[)", text)[1:]
        entries.sort(key=lambda e: e[4:14])
        for e in entries[-a.last:]:
            print(e.splitlines()[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
