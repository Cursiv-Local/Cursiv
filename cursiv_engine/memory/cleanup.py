"""
Show-and-confirm clean-up of saved context that misleads answers.

Saved notes (strands.jsonl) and memory facts (memory_facts.jsonl) are put into
the model's prompt as "related earlier conversations" and "what you remember".
Some records do more harm than good there:

  * guardian-era replies describing parts of Cursiv that no longer exist
    ("System Guardian: ARMED", "EvoCore", "JWArchitectCore" ...);
  * old council answers about Cursiv's own features, which go stale;
  * test records ("persistence test", test IDs);
  * inferred guesses about what the person wants from AI (not their words);
  * style "rules" that are really captured content (a heading, a numbered list
    item, a long passage) or exact duplicates -- these are added to every answer.

`memory cleanup` only lists them. `memory cleanup remove <codes>` or
`memory cleanup remove all` removes what the person picked: each record is first
copied to APP_DATA/backups/memory-cleanup-<time>/ (encrypted when encrypted
storage is on), then removed with a verified write. Nothing is removed without
that command, and nothing is flagged by a model: the rules below are plain text
patterns anyone can read.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

GUARDIAN_ERA = re.compile(
    r"(?i)system guardian|constitutional ✓|\bevocore\b|jwarchitectcore|funforge|robot language filter|"
    r"council:\s*14/14|identity drift|vtankfsm|default meta|constitutional guardrails|evolution:\s*active|"
    r"\bmetas\b|meta-programming framework")
CURSIV_FEATURES = re.compile(
    r"(?i)(?:features?|tools?) (?:already )?(?:available|that already exist) in (?:cursiv|this install)|"
    r"using only (?:the )?(?:specified tools|features that already exist)|cursiv's [a-z]+ feature")
TEST_RECORD = re.compile(
    r"(?i)\btest id\b|persistence (?:test|marker|check)|\busb-persist|\bc4-persist|"
    r"\b(?:this is|just) a (?:test|persistence test)\b|\btest marker\b|"
    r"\bnow (?:list|forget|read|show) (?:the|that|my)\b")
# An inferred preference *against* kinds of thinking (it can prime refusals). Facts about
# the person's projects that merely mention AI capabilities are not flagged.
AI_PREFERENCE_GUESS = re.compile(
    r"(?i)\b(?:prioriti[sz]\w*|prefer\w*|avoid\w*|dislik\w*|(?:does ?n[o']t|do not) want|over)\b[^.]{0,80}"
    r"\b(?:speculative|abstract|hypothetical|imaginative|creative)\b")
# "... Cursiv, a local AI assistant built by <a person>": a guess, and it names someone.
MADE_BY = re.compile(r"(?i)\bcursiv\b[^.]{0,80}\b(?:built|made|created|developed|written)\s+by\b")


STYLE_CONTENT = re.compile(r"^\s*(?:#{1,6}\s|\d+[.)]\s|[-*•]\s|rule\s*:)", re.I)


def _style_code(text: str) -> str:
    import hashlib
    return "style-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def _preview(text: str, n: int = 140) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def scan(person: str) -> list[dict]:
    """Flagged records, each {code, store, id, reason, preview}. Reads only."""
    from cursiv_engine.core import strand_store
    from cursiv_engine.memory import semantic
    found: list[dict] = []
    for s in strand_store.list_strands(limit=100000):
        body = f"{s.get('query', '')}\n{s.get('synthesis', '') or s.get('strand', '')}"
        if GUARDIAN_ERA.search(body):
            reason = "guardian-era reply describing parts of Cursiv that no longer exist"
        elif s.get("source") in ("council", "async_council") and CURSIV_FEATURES.search(body):
            reason = "old council answer about Cursiv's own features (may be outdated)"
        elif TEST_RECORD.search(body):
            reason = "test record"
        else:
            continue
        found.append({"store": "note", "id": str(s.get("id")), "reason": reason,
                      "preview": _preview(s.get("query") or body)})
    for f in semantic.list_facts(person):
        text = f.get("text", "")
        if TEST_RECORD.search(text):
            reason = "test record"
        elif semantic.origin_of(f) == "inferred" and AI_PREFERENCE_GUESS.search(text):
            reason = "inferred guess about what you want from AI (not something you said)"
        elif semantic.origin_of(f) == "inferred" and MADE_BY.search(text):
            reason = "inferred claim about who made Cursiv (not something you said)"
        else:
            continue
        found.append({"store": "memory", "id": str(f.get("id")), "reason": reason, "preview": _preview(text)})
    for item in found:
        item["code"] = item["id"]
    try:
        from cursiv_engine.core import style
        seen = set()
        for rule in style.load(person).get("rules", []):
            text = str(rule.get("text", ""))
            key = " ".join(text.lower().split())
            if STYLE_CONTENT.search(text) or len(text) > 180:
                reason = "style preference that is really captured content (added to every answer)"
            elif key in seen:
                reason = "duplicate style preference"
            else:
                seen.add(key)
                continue
            seen.add(key)
            found.append({"store": "style", "id": text, "code": _style_code(text), "reason": reason,
                          "preview": _preview(text)})
    except (OSError, ValueError):  # best-effort: a read-only suggestion list; nothing is changed
        pass
    return found


def describe(items: list[dict]) -> str:
    if not items:
        return "Nothing to clean up: no saved notes or memories match the clean-up rules."
    rows = ["These saved records are put into answers but look misleading. Nothing has been changed.", ""]
    for it in items:
        kind = {"note": "Saved note", "memory": "Memory", "style": "Style preference"}[it["store"]]
        rows.append(f"- `{it['code']}` · {kind} · {it['reason']}\n  “{it['preview']}”")
    rows += ["", "Remove some: memory cleanup remove <code> <code> …",
             "Remove all of these: memory cleanup remove all",
             "Removed records are copied to a backup folder first."]
    return "\n".join(rows)


def remove(person: str, codes: list[str] | None) -> str:
    """codes=None removes everything currently flagged. Archives first; returns a receipt."""
    from cursiv_engine.core import atomic, private_store, strand_store
    from cursiv_engine.core.paths import APP_DATA
    from cursiv_engine.memory import semantic
    items = scan(person)
    if codes is not None:
        wanted = set(codes)
        unknown = wanted - {it["code"] for it in items}
        if unknown:
            return ("Not removed: " + ", ".join(sorted(unknown)) + " isn't in the current clean-up list. "
                    "Run memory cleanup to see it again.")
        items = [it for it in items if it["code"] in wanted]
    if not items:
        return "Nothing was removed: nothing selected matches the clean-up rules."
    folder = APP_DATA / "backups" / time.strftime("memory-cleanup-%Y%m%d-%H%M%S")
    notes = [it["id"] for it in items if it["store"] == "note"]
    facts = [it["id"] for it in items if it["store"] == "memory"]
    removed_notes = strand_store.remove_strands(notes, folder / "strands.jsonl") if notes else []
    removed_facts: list[dict] = []
    if facts:
        by_id = {f["id"]: f for f in semantic.list_facts(person, include_superseded=True)}
        data = "".join(json.dumps(by_id[i], ensure_ascii=False) + "\n" for i in facts if i in by_id).encode("utf-8")
        archive = folder / "memory_facts.jsonl"
        atomic.write_bytes(archive, data)
        if private_store.read_bytes(archive) != data:
            raise OSError("Memory archive read-back verification failed; no memory was removed")
        removed_facts = semantic.forget_selected(facts, person=person)
    removed_style = _remove_style(person, [it for it in items if it["store"] == "style"])
    lines = [f"Removed {len(removed_notes)} saved note(s), {len(removed_facts)} memory record(s)"
             f" and {len(removed_style)} style preference(s)."]
    lines += [f"- {r.get('id')}: {_preview(r.get('query') or r.get('text'), 90)}" for r in removed_notes + removed_facts]
    lines += [f"- style: {_preview(t, 90)}" for t in removed_style]
    lines.append(f"Copies are in {folder}.")
    return "\n".join(lines)


def _remove_style(person: str, items: list[dict]) -> list[str]:
    """Drop flagged style rules (first occurrence of a duplicate is kept). The removed
    rules are copied into the style folder's backups first (vault-covered)."""
    if not items:
        return []
    from cursiv_engine.core import atomic, private_store, style
    with style._lock:
        data = style.load(person)
        rules = data.get("rules", [])
        drop, seen, kept, gone = {it["id"] for it in items}, set(), [], []
        dup_only = {it["id"] for it in items if it["reason"] == "duplicate style preference"}
        for rule in rules:
            text = str(rule.get("text", ""))
            key = " ".join(text.lower().split())
            first = key not in seen
            seen.add(key)
            if text in drop and not (text in dup_only and first):
                gone.append(rule)
            else:
                kept.append(rule)
        if not gone:
            return []
        archive = style._path(person).parent / "backups" / time.strftime(f"cleanup-%Y%m%d-%H%M%S-{style._path(person).stem}.json")
        payload = json.dumps(gone, ensure_ascii=False, indent=1).encode("utf-8")
        atomic.write_bytes(archive, payload)
        if private_store.read_bytes(archive) != payload:
            raise OSError("Style archive read-back verification failed; no style preference was removed")
        data["rules"] = kept
        style._save(person, data)
    return [str(r.get("text", "")) for r in gone]


def command(text: str, person: str) -> str | None:
    """`memory cleanup` / `memory cleanup remove …`. None if the text isn't one."""
    t = " ".join((text or "").split())
    low = t.lower()
    if low in ("memory cleanup", "memory clean up", "clean up memory", "cleanup memory"):
        return describe(scan(person))
    if low.startswith("memory cleanup remove"):
        rest = t[len("memory cleanup remove"):].strip()
        if not rest:
            return "Say which: memory cleanup remove <code> … (codes from memory cleanup), or memory cleanup remove all"
        codes = None if rest.lower() == "all" else [c.strip("`,;") for c in rest.split() if c.strip("`,;")]
        return remove(person, codes)
    return None
