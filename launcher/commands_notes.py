"""Notes commands.

handle(runtime, text, cmd, cfg, history) returns a command result,
an intentional None (defer to chat), or UNHANDLED. Called in the
original precedence order by command_dispatch; no widgets are loaded.
"""
from __future__ import annotations

from cursiv_engine.core.command_api import CommandRuntime, UNHANDLED


def handle(runtime: CommandRuntime, text: str, cmd: str, cfg: dict, history: list[dict]):
    if cmd == "anchor this" or cmd.startswith("anchor this "):
        if not runtime._STRAND_OK:
            return runtime.TextResult("Saved notes aren't available.")
        parts = cmd.split()
        territory = parts[2] if len(parts) >= 3 else "general"
        if territory != "general" and territory not in runtime._strand_territories():
            territory = "general"
        if not history:
            return runtime.TextResult("No session history to anchor.")
        last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
        last_ai = next((m["content"] for m in reversed(history) if m["role"] == "assistant"), "")
        if not (last_user or last_ai):
            return runtime.TextResult("Nothing to anchor yet — send a message first.")
        sid = runtime._strand_save(last_user, last_ai, tags=["anchor"], score=0.85,
                            territory_tag=territory, source="anchor", model="gui")
        if not sid:
            return runtime.TextResult('Note save not confirmed. No saved-note ID was returned; check Saved Notes before retrying.')
        return runtime.TextResult(f"Saved as note {sid}" + (f"  [{territory}]" if territory != "general" else ""))

    if cmd == "strands" or cmd.startswith("strands "):
        if not runtime._STRAND_OK:
            return runtime.TextResult("Saved notes aren't available.")
        sub = text[8:].strip() if cmd.startswith("strands ") else ""
        if sub.startswith("search "):
            q = sub[7:].strip()
            if not q:
                return runtime.TextResult("Usage: notes search <words>")
            return runtime.TextResult(f"Notes search — {q}\n\n" + (runtime._strand_fmt(runtime._strand_search(q)) or "No matches."))
        if sub and sub in runtime._strand_territories():
            results = runtime._strand_list(territory=sub, limit=20)
            return runtime.TextResult(f"Notes [{sub}] ({len(results)} found)\n\n" + (runtime._strand_fmt(results) or "None yet."))
        total = runtime._strand_count()
        counts = runtime._strand_terr_counts()
        recent = runtime._strand_list(limit=8)
        counts_line = "  ".join(f"{t}:{n}" for t, n in counts.items()) if counts else "none yet"
        out = f"Saved notes — {total}\n{counts_line}"
        if recent:
            out += "\n\n" + runtime._strand_fmt(recent)
        return runtime.TextResult(out)

    if cmd.startswith("strand export") or cmd == "strand export":
        if not (runtime._STRAND_OK and runtime._SFED_OK):
            return runtime.TextResult("Note export isn't available.")
        parts = cmd.split()
        territory = parts[2] if len(parts) >= 3 else None
        all_s = runtime._strand_list(territory=territory, limit=5000)
        if not all_s:
            t_label = f" in '{territory}'" if territory else ""
            return runtime.TextResult(f"No notes{t_label} to export.")
        terr_defs = runtime._strand_territories()
        label = f"cursiv-{territory or 'all'}"
        pack_text = runtime._sfed_export(all_s, terr_defs, label=label)
        out_path = runtime._CHAT_ROOT / f"{label}-{int(runtime.datetime.now().timestamp())}{runtime._PACK_EXT}"
        try:
            out_path.write_text(pack_text, encoding="utf-8")
        except Exception as e:
            return runtime.TextResult(f"Export failed: {e}")
        t_label = territory or "all topics"
        return runtime.TextResult(
            f"Notes exported\nFile    :  {out_path.name}\n"
            f"Notes   :  {len(all_s)}\nScope   :  {t_label}\n\n"
            f"Transfer via USB / LAN. Import with:  note import {out_path.name}"
        )

    if cmd.startswith("strand import "):
        if not (runtime._STRAND_OK and runtime._SFED_OK):
            return runtime.TextResult("Note export isn't available.")
        pack_path = runtime.Path(text[14:].strip().strip('"').strip("'"))
        if not pack_path.is_absolute() and not pack_path.exists():
            # "strand export" always writes into _CHAT_ROOT and tells the
            # user to import the bare filename back -- the terminal CLI
            # gets away with resolving that relative to cwd because it's
            # always launched from the repo root, but the packaged GUI's
            # cwd isn't guaranteed to match, so fall back to where the
            # file would actually have landed.
            fallback = runtime._CHAT_ROOT / pack_path
            if fallback.exists():
                pack_path = fallback
        if not pack_path.exists():
            return runtime.TextResult(f"File not found: {pack_path}")
        try:
            pack_text = pack_path.read_text(encoding="utf-8")
            in_strands, _in_terr, meta = runtime._sfed_import(pack_text)
        except ValueError as e:
            return runtime.TextResult(f"Pack verification failed: {e}")
        except Exception as e:
            return runtime.TextResult(f"Import failed: {e}")
        imported = 0
        for s in in_strands:
            try:
                runtime._strand_save(
                    s.get("query", ""), s.get("synthesis", ""),
                    tags=(s.get("tags") or []) + ["federated_import"],
                    score=s.get("score", 0.70),
                    territory_tag=s.get("territory_tag", "general"),
                    source="federation", model=s.get("model", "unknown"),
                    provenance={"source_models": [s.get("model", "?")],
                                "federated": True, "pack_label": meta.get("label", "?")},
                )
                imported += 1
            except Exception:
                pass
        note = ""
        if not meta.get("same_machine"):
            note = "\n(Cross-machine pack — signature does not match this instance; expected for transfers between machines.)"
        return runtime.TextResult(f"Notes import\n{runtime._sfed_summary(in_strands, meta)}\n\nImported {imported}/{len(in_strands)} notes.{note}")

    if cmd == "queue" or cmd.startswith("queue "):
        if not runtime._QUEUE_OK:
            return runtime.TextResult("Offline Queue not available.")
        sub = text[6:].strip() if cmd.startswith("queue ") else ""
        if not sub or sub == "list":
            return runtime.TextResult(runtime._queue_format() or "Queue is empty.")
        if sub.startswith("add "):
            task = sub[4:].strip()
            if not task:
                return runtime.TextResult("Usage: queue add <task>")
            entry = runtime._queue_enqueue(task)
            return runtime.TextResult(f"Queued:  {entry.get('id', '?')} — {task[:60]}")
        if sub == 'flush':
            from cursiv_engine.agents import queue_executor
            return queue_executor.command(runtime, cfg)
        if sub.startswith(('cancel ', 'retry ')):
            from cursiv_engine.agents import offline_queue
            parts = sub.split()
            try:
                row = (offline_queue.cancel(parts[1]) if parts[0] == 'cancel' else
                       offline_queue.retry(parts[1], reconciled='--reconciled' in parts[2:]))
                return runtime.TextResult(row['id'] + ' [' + row['status'] + ']')
            except Exception as exc:
                return runtime.TextResult(f'Queue unchanged: {type(exc).__name__}: {exc}')
        return runtime.TextResult('Usage: queue list | queue add <task> | queue flush | queue cancel <ID> | '
                                  'queue retry <ID> [--reconciled]. Flush uses only local read-only profiles.')

    if cmd.startswith("remember ") or cmd == "remember":
        if not runtime._STRAND_OK:
            return runtime.TextResult("Saved notes aren't available.")
        q = text[9:].strip()
        if not q:
            return runtime.TextResult("Type remember <something> to save it, or what do you remember to see what I know.")
        results = runtime._strand_search(q, top_k=5, min_score=0.08)
        if not results:
            return runtime.TextResult("No matching notes. Save an answer with: save this")
        return runtime.TextResult(f"Local memory — {q}\n\n" + runtime._strand_fmt(results))

    if cmd.startswith("rate"):
        parts = cmd.split()
        score = None
        if len(parts) >= 2:
            tok = parts[1]
            if tok == "good":
                score = 5
            elif tok == "bad":
                score = 1
            elif tok.isdigit() and 1 <= int(tok) <= 5:
                score = int(tok)
        if score is None:
            return runtime.TextResult("Usage: rate good  ·  rate bad  ·  rate 1-5")
        if not history:
            return runtime.TextResult("No exchange to rate yet.")
        return runtime.TextResult(f"Rated {'★' * score}{'☆' * (5 - score)}  ({score}/5)")

    # ── Babel translation ────────────────────────────────────────────────
    return UNHANDLED
