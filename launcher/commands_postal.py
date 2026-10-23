"""Postal commands.

handle(runtime, text, cmd, cfg, history) returns a command result,
an intentional None (defer to chat), or UNHANDLED. Called in the
original precedence order by command_dispatch; no widgets are loaded.
"""
from __future__ import annotations

from cursiv_engine.core.command_api import CommandRuntime, UNHANDLED


def handle(runtime: CommandRuntime, text: str, cmd: str, cfg: dict, history: list[dict]):
    if cmd == "letters" or cmd in ("letters for me", "letters from me"):
        if not runtime._POSTAL_OK:
            return runtime.TextResult("Postal module unavailable.")
        postal_user = cfg.get("postal_user", "joshua")
        if cmd == "letters for me":
            llist, heading = runtime._postal_for(postal_user), f"LETTERS FOR {postal_user.upper()}"
        elif cmd == "letters from me":
            llist, heading = runtime._postal_from(postal_user), f"LETTERS FROM {postal_user.upper()}"
        else:
            llist, heading = runtime._postal_all(), "ALL SEALED LETTERS"
        if not llist:
            return runtime.TextResult(f"{heading}\n\nNo sealed letters found.")
        lines = [f"{heading}"]
        for e in llist:
            badge = "read" if e.get("read") else "unread"
            hint = f"  ({e['hint']})" if e.get("hint") else ""
            lines.append(
                f"{e['id']}  {e.get('from_display', '?')} → {e.get('for_display', '?')}  "
                f"{e.get('sealed', '')[:10]}  {badge}{hint}"
            )
        return runtime.TextResult("\n".join(lines))

    if cmd.startswith("open letter ") or cmd.startswith("letter "):
        if not runtime._POSTAL_OK:
            return runtime.TextResult("Postal module unavailable.")
        lid = (text[12:] if cmd.startswith("open letter ") else text[7:]).strip()
        if not lid:
            return runtime.TextResult("Usage: open letter <id>")
        entry = runtime._postal_entry(lid)
        if not entry:
            return runtime.TextResult(f"Letter {lid} not found.")
        body = runtime._postal_open(lid)
        if body is None:
            return runtime.TextResult("Decryption failed. This seal cannot be opened on this machine.")
        sig = {
            "verified": "✓ VERIFIED", "verified_rotated": "✓ VERIFIED (signed with sender's prior key)",
            "verified_compromised": "⟳ COHERENCE DEGRADED (signed with a compromised key)",
            "unverified": "~ unverified (sender not in contacts)",
            "unsigned": "unsigned (pre-identity letter)", "INVALID": "✗ SIGNATURE INVALID",
        }.get(runtime._postal_sig_status(lid), runtime._postal_sig_status(lid))
        header = f"from: {entry.get('from_display', '?')}  to: {entry.get('for_display', '?')}  {entry.get('sealed', '')[:10]}\n{sig}"
        if entry.get("hint"):
            header += f"\nhint: {entry['hint']}"
        return runtime.TextResult(f"{header}\n\n{body}")

    if cmd.startswith("council letter "):
        if not runtime._POSTAL_OK:
            return runtime.TextResult("Postal module unavailable.")
        lid = text[15:].strip()
        if not lid:
            return runtime.TextResult("Usage: council letter <id>")
        postal_user = cfg.get("postal_user", "joshua")
        reading = runtime._postal_council(lid, postal_user, cfg)
        return runtime.TextResult(reading)

    if cmd.startswith("seal export "):
        if not runtime._POSTAL_OK:
            return runtime.TextResult("Postal module unavailable.")
        lid = text[12:].strip()
        result = runtime._postal_export(lid)
        if result is None:
            return runtime.TextResult("Export failed — letter not found or cannot decrypt.")
        pack_path, passphrase = result
        return runtime.TextResult(
            f"Sealpack exported\nfile: {pack_path}\npassphrase: {passphrase}\n\n"
            "Share this passphrase with the recipient out-of-band. It is shown once and never stored."
        )

    if cmd.startswith("seal import "):
        if not runtime._POSTAL_OK:
            return runtime.TextResult("Postal module unavailable.")
        rest = text[12:].strip()
        # Last whitespace-separated token is the passphrase; everything
        # before it is the (possibly space-containing) file path.
        parts = rest.rsplit(None, 1)
        if len(parts) != 2:
            return runtime.TextResult("Usage: seal import <filepath> <passphrase>")
        pack_file, passphrase = parts
        new_id = runtime._postal_import(pack_file.strip('"').strip("'"), passphrase)
        if new_id is None:
            return runtime.TextResult("Import failed — wrong passphrase or corrupted pack.")
        return runtime.TextResult(f"Sealed locally as: {new_id}")

    if cmd == "postal user" or cmd.startswith("postal user "):
        new_user = text[12:].strip().lower() if cmd.startswith("postal user ") else ""
        if not new_user:
            return runtime.TextResult(f"Current postal identity: {cfg.get('postal_user', 'joshua')}")
        cfg["postal_user"] = new_user
        return runtime.TextResult(f"Postal identity set to: {new_user}")

    if cmd.startswith("postal setup ") or cmd == "postal setup":
        if not runtime._POSTAL_OK:
            return runtime.TextResult("Postal module unavailable.")
        name = text[13:].strip() if cmd.startswith("postal setup ") else ""
        if not name:
            return runtime.TextResult("Usage: postal setup <your name>")
        try:
            meta = runtime._postal_setup(name)
        except Exception as e:
            return runtime.TextResult(f"Setup failed: {e}")
        cfg["postal_user"] = meta.get("name", name).lower()
        return runtime.TextResult(
            f"Identity created\nName: {meta.get('name', name)}\nKey ID: {meta.get('key_id', '?')[:8]}\n"
            f"Public: {meta.get('pubkey', '?')}\n\n"
            f"Share this public key with anyone you want to receive letters from. "
            f"They add you with: postal add user {name} <your key>"
        )

    if cmd == "postal my key":
        if not runtime._POSTAL_OK:
            return runtime.TextResult("Postal module unavailable.")
        my_id = runtime._postal_my_id()
        if not my_id:
            return runtime.TextResult("No identity set up yet. Run: postal setup <your name>")
        return runtime.TextResult(
            f"Your Cursiv identity\nName: {my_id.get('name', '?')}\n"
            f"Key ID: {my_id.get('key_id', '?')[:8]}\nPublic: {my_id.get('pubkey', '?')}"
        )

    if cmd.startswith("postal add user ") or cmd == "postal add user":
        if not runtime._POSTAL_OK:
            return runtime.TextResult("Postal module unavailable.")
        parts = text[16:].strip().split() if cmd.startswith("postal add user ") else []
        if len(parts) < 2:
            return runtime.TextResult("Usage: postal add user <name> <pubkey>")
        try:
            entry = runtime._postal_add_contact(parts[0], parts[1])
        except ValueError as e:
            return runtime.TextResult(f"Invalid public key: {e}")
        return runtime.TextResult(f"Contact added: {parts[0]}  (key-id: {entry.get('key_id', '?')[:8]})")

    if cmd.startswith("postal remove user "):
        if not runtime._POSTAL_OK:
            return runtime.TextResult("Postal module unavailable.")
        name = text[19:].strip()
        ok = runtime._postal_rm_contact(name)
        return runtime.TextResult(f"Contact removed: {name}" if ok else f"Contact not found: {name}")

    if cmd.startswith("postal rotate") or cmd == "postal rotate key":
        if not runtime._POSTAL_OK:
            return runtime.TextResult("Postal module unavailable.")
        compromised = "compromised" in cmd or "leaked" in cmd
        reason = "key compromised — attacker may have private key" if compromised else "manual rotation"
        try:
            rot = runtime._postal_rotate(reason=reason, compromised=compromised)
        except Exception as e:
            return runtime.TextResult(f"Rotation failed: {e}")
        if not rot:
            return runtime.TextResult("Rotation failed — no identity set up. Run: postal setup <name>")
        note = (
            "\n\nCoherence degradation will activate on the retired key — any letter later "
            "read through it returns shifted content. The attacker sees output, not truth."
            if compromised else ""
        )
        return runtime.TextResult(
            f"Key rotation\nOld key ID: {rot.get('old_key_id', '?')[:8]} (archived locally)\n"
            f"New key ID: {rot.get('new_key_id', '?')[:8]}\nNew public: {rot.get('new_pubkey', '?')}\n\n"
            f"Update your contacts: postal add user <your name> <new key>{note}"
        )

    if cmd == "postal key history":
        if not runtime._POSTAL_OK:
            return runtime.TextResult("Postal module unavailable.")
        hist = runtime._postal_key_history()
        if not hist:
            return runtime.TextResult("Key history\n\nNo retired keys.")
        lines = ["Key history"]
        for hk in hist:
            flag = "  COMPROMISED — coherence degradation active" if hk.get("compromised") else ""
            lines.append(f"{hk.get('key_id', '?')[:8]}  retired:{hk.get('retired_at', '?')[:10]}  {hk.get('reason', '?')[:40]}{flag}")
        return runtime.TextResult("\n".join(lines))

    if cmd == "postal contacts":
        if not runtime._POSTAL_OK:
            return runtime.TextResult("Postal module unavailable.")
        clist = runtime._postal_contacts()
        if not clist:
            return runtime.TextResult("Contacts\n\nNo contacts yet. Use: postal add user <name> <pubkey>")
        lines = [f"Contacts ({len(clist)})"]
        for c in clist:
            lines.append(f"{c['name']:<16}  id:{c.get('key_id', '?')[:8]}  added:{c.get('added', '?')[:10]}")
        return runtime.TextResult("\n".join(lines))

    if cmd.startswith("legacy import "):
        imp_path = text[14:].strip().strip('"').strip("'")
        if not imp_path:
            return runtime.TextResult("Usage: legacy import <path to .legacypack file>")
        try:
            count, skipped = runtime._legacy_import_pack(imp_path)
        except (FileNotFoundError, ValueError) as e:
            return runtime.TextResult(str(e))
        except Exception as e:
            return runtime.TextResult(f"Import failed: {e}")
        if count == 0 and not skipped:
            return runtime.TextResult("No letters found in pack.")
        out = []
        if count:
            out.append(f"Imported {count} letter(s).")
        if skipped:
            out.append(f"Skipped {len(skipped)} duplicate(s): " + ", ".join(skipped))
        out.append("Letters are now in the vault.")
        return runtime.TextResult("\n".join(out))

    # ── Image generation (paid OpenAI key only) ─────────────────────────
    # Offline/local models and the free keys can't generate images -- say so
    # plainly instead of letting a text model pretend it drew something.
    return UNHANDLED
