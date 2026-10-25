"""
What a profile is given to read (U101 starter profiles).

A profile never calls a tool. Cursiv's code reads what the profile's `reads:` line allows --
the field notebook, imported documents, a calculation -- and puts it in front of the model,
read-only. Saving, correcting and deleting stay with Cursiv's own commands and confirm cards.

The Data checker's findings are worked out here, by code: duplicate sample IDs, readings with no
unit, values that aren't numbers, entries with neither site nor sample. The model only explains them.
"""
from __future__ import annotations

import re
from collections import defaultdict

READS = ("notebook", "documents", "calculations")      # all read-only
MAX_RECORDS = 60
_NO_UNIT_OK = re.compile(r"(?i)\b(?:ph|count|counts|number|n|score|index|ratio)\b")


def _current() -> list[dict]:
    from cursiv_engine.core import fieldlog
    return fieldlog.current()


def findings(rows: list[dict] | None = None) -> list[str]:
    """Problems Cursiv's code finds in the notebook's current records, each with its record ID."""
    rows = _current() if rows is None else rows
    out = []
    by_sample = defaultdict(list)
    for r in rows:
        if r.get("sample_id"):
            by_sample[r["sample_id"].casefold()].append(r)
    for group in by_sample.values():
        if len(group) > 1:
            out.append(f"Sample ID {group[0]['sample_id']} is used by {len(group)} current records: "
                       + ", ".join(f"[{r['id']}]" for r in group) + ".")
    for r in rows:
        for m in r.get("measurements") or []:
            if m.get("number") is None:
                out.append(f"[{r['id']}] {m['name']} is \"{m['value']}\", not a number, so it can't be used in calculations.")
            elif not (m.get("unit") or "").strip() and not _NO_UNIT_OK.search(m["name"]):
                out.append(f"[{r['id']}] {m['name']} {m['value']} has no unit.")
        if not r.get("site") and not r.get("sample_id"):
            out.append(f"[{r['id']}] has neither a site nor a sample ID.")
    return out


def notebook_block(question: str = "", *, checks: bool = False) -> str:
    from cursiv_engine.core import fieldlog
    problems = fieldlog.verify()
    rows = _current()
    lines = ["## Field notebook (read only; supplied by Cursiv's code)"]
    if problems:
        lines.append("The notebook's integrity check found problems, so its records are not shown: "
                     + "; ".join(problems[:5]))
        return "\n".join(lines)
    if not rows:
        lines.append("The notebook has no entries.")
    else:
        shown = rows[-MAX_RECORDS:]
        lines.append(f"{len(rows)} current record(s); the integrity chain was verified. "
                     + (f"The latest {len(shown)} are shown." if len(shown) < len(rows) else "All are shown."))
        lines += ["[" + r["id"] + "] " + fieldlog.summary(r) for r in shown]
    if checks:
        found = findings(rows)
        lines.append("\n## Findings from Cursiv's checks (code, not the model)")
        lines += [f"- {f}" for f in found] or ["- The checks Cursiv ran (duplicate sample IDs, missing units, "
                                                "non-numeric values, missing site and sample) found nothing."]
    return "\n".join(lines)


def documents_block(question: str) -> tuple[str, bool]:
    """(block, found anything). Passages from the imported documents that match the question."""
    from cursiv_engine.core import documents
    if not documents.library():
        return "## Your documents\nNo documents are imported.", False
    found = documents.search(question, stem=True)
    if not found:
        names = ", ".join(d["name"] for d in documents.library())
        return f"## Your documents\nNo passage in your imported documents ({names}) matches this question.", False
    return documents.prompt_block(found, True), True


def calculation_block(question: str) -> str:
    from cursiv_engine.core import calc
    w = calc.work_out(question)
    return calc.prompt_note(w) if w else ""


_DECIMAL = re.compile(r"(?<![\w.])(-?\d+\.\d+)(?![\w.])")
_UNIT_AFTER = r"\s*(°\s?[CF]|mg/?L|ppm|NTU|µS/cm|uS/cm|%|m|cm|mm|ml|mL|L)\b"


def answer_note(answer: str, supplied: str, agent: dict) -> str:
    """After a notebook-reading profile answers: numbers it gives that aren't in what Cursiv supplied,
    and units it adds to readings recorded without one (the Report writer wrote "2.1 mg/L" for a
    nitrate recorded as plain 2.1). One line for under the answer, or ""."""
    if "notebook" not in (agent.get("reads") or []):
        return ""
    have = set(_DECIMAL.findall(supplied or ""))
    new = [n for n in dict.fromkeys(_DECIMAL.findall(answer or "")) if n not in have]
    added = []
    for r in _current():
        for m in r.get("measurements") or []:
            if m.get("number") is not None and not (m.get("unit") or "").strip() and not _NO_UNIT_OK.search(m["name"]):
                hit = re.search(re.escape(m["value"]) + _UNIT_AFTER, answer or "")
                if hit:
                    added.append(f"{m['name']} {m['value']} was recorded with no unit, but the answer says {hit.group(0).strip()}")
    bits = []
    if new:
        bits.append("these numbers aren't in your records or documents: " + ", ".join(new[:6]))
    bits += added[:3]
    if not bits:
        return ""
    return "*(Cursiv's check of this answer against your records: " + "; ".join(bits) + ".)*"


def context(agent: dict, question: str) -> tuple[str, str]:
    """(text for the profile's prompt, a reply Cursiv gives itself instead of the model, or "")."""
    reads = [r for r in agent.get("reads") or [] if r in READS]
    parts = []
    if "notebook" in reads:
        parts.append(notebook_block(question, checks=agent.get("name") == "checker"))
    if "documents" in reads:
        block, hit = documents_block(question)
        parts.append(block)
        if not hit and agent.get("name") == "protocol":
            return "", ("Your imported documents don't cover that, so the Protocol helper won't answer from "
                        "general knowledge (your protocol may differ).\n\n*[Sources: your documents (no AI model)]*")
    if "calculations" in reads:
        note = calculation_block(question)
        if note:
            parts.append(note)
    return "\n\n".join(p for p in parts if p), ""
