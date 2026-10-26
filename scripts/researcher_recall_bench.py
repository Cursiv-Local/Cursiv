"""Measure native recall on synthetic records; no model or real user data.

Run with --out bench/results/U106-researcher-recall-before.json, then after.
Homes and app data are redirected before importing any Cursiv module.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
from time import perf_counter
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "launcher"), str(ROOT / "bench" / "researcher")]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    output = Path(args.out)
    if output.exists():
        raise SystemExit("Refusing to overwrite evidence")
    home = Path(tempfile.mkdtemp(prefix="cursiv-u106-recall-"))
    os.environ["HOME"] = os.environ["USERPROFILE"] = str(home)
    os.environ["CURSIV_APP_DATA"] = str(home / "app-data")
    from recall_cases import CASES
    from cursiv_engine.core import fieldlog, field_recall, notebook_tools
    today = date.today()
    yesterday = today - timedelta(days=1)
    last_tuesday = today - timedelta(days=(today.weekday() - 1) % 7 or 7)
    specifications = [
        ("WB-001", "Willow Basin", "water temp", "21.4", yesterday, "cloudy"),
        ("WB-002", "Willow Basin", "soil temp", "17.5", yesterday, "dry soil"),
        ("EM-001", "East Meadow", "water temp", "19.2", yesterday, "clear"),
        ("WB-003", "Willow Basin", "water temp", "22.0", today, "clear"),
        ("WB-004", "Willow Basin", "water temp", "18.0", last_tuesday, "clear"),
    ]
    records = []
    for sample, site, measurement, value, day, note in specifications:
        stamp = datetime.combine(day, time(12)).astimezone().timestamp()
        # Only the synthetic record's clock is controlled, never model answers.
        with patch.object(fieldlog.time, "time", return_value=stamp):
            records.append(fieldlog.add(sample_id=sample, site=site,
                measurements=[dict(name=measurement, value=value, unit="C")], note="Synthetic fixture: " + note))
    original = fieldlog.log_file().read_bytes()
    assert fieldlog.verify() == []
    rows = []
    for name, question, expected in CASES:
        started = perf_counter()
        native = notebook_tools.command(question, [])
        answer = native.render() if native is not None else field_recall.command(question)
        elapsed = perf_counter() - started
        selected = sorted(record["sample_id"] for record in records if answer and record["id"] in answer)
        ok = answer is None if expected is None else answer is not None and selected == sorted(expected)
        rows.append(dict(name=name, question=question, expected_samples=expected,
                         selected_samples=selected, handled=answer is not None, ok=ok,
                         answer=answer, seconds=elapsed))
    assert fieldlog.log_file().read_bytes() == original
    positives = [row for row in rows if row["expected_samples"] is not None]
    negatives = [row for row in rows if row["expected_samples"] is None]
    result = dict(method="Native notebook lookup on synthetic records; no model calls or human usability claim",
                  date=str(today), isolated_home=str(home), records=records,
                  question_sha256=hashlib.sha256((ROOT / "bench/researcher/recall_cases.py").read_bytes()).hexdigest(),
                  score=dict(exact_selection=f"{sum(row['ok'] for row in positives)}/{len(positives)}",
                             negatives_preserved=f"{sum(row['ok'] for row in negatives)}/{len(negatives)}",
                             total=f"{sum(row['ok'] for row in rows)}/{len(rows)}",
                             median_seconds=statistics.median(row["seconds"] for row in rows)), rows=rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result["score"], indent=2))


if __name__ == "__main__":
    main()
