"""
Bring a Cursiv drive's personal data up to date from this computer -- without
losing anything on either side.

This computer keeps Cursiv's data in two folders: paths.APP_DATA (settings, keys,
memories; next to the program) and ~/.cursiv (conversations, field log, documents).
On a drive both live in <drive>\\Home\\.cursiv. Older copies of a few files can sit
in both computer folders; the newer one is the one Cursiv uses.

plan() only reads. For every file it decides:
    add      the drive doesn't have it
    same     identical bytes
    update   this computer's copy is newer, or the drive's copy is an earlier part
             of it (a log this computer added lines to)
    keep     the drive's copy is newer, or this computer's copy is an earlier part
             of it (the drive was used since the last update) -- left alone
apply() copies add/update files. A drive file is copied into
Home\\.cursiv\\backups\\usb-update-<time>\\ and verified before it is replaced, and
every new file is checked byte for byte against its source.

The other direction (work done on the drive back to this computer) uses the same
decisions: plan_import(), stage_import() and, at the next start,
apply_pending_import() -- see the section at the end.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path

MTIME_SLACK = 2.0                      # FAT-family drives store times in 2-second steps
# The live process lease, and each computer's own encryption configuration: a
# computer's data is always encrypted (U97), a drive's stays readable, so stores
# are decrypted on the way to a drive and encrypted again on the way back.
SKIP_NAMES = {".vault-lease", "data-vault.json"}
SKIP_TOP = {"backups", "import-pending"}  # each side keeps its own recovery copies and staging


def data_sources() -> list[Path]:
    """This computer's Cursiv data folders, most authoritative first."""
    from cursiv_engine.core import paths
    out = []
    for p in (paths.APP_DATA, Path.home() / ".cursiv"):
        try:
            p = p.resolve()
        except OSError:
            continue
        if p.is_dir() and p not in out:
            out.append(p)
    return out


def _linked(p: Path) -> bool:
    return p.is_symlink() or p.is_junction()


def collect(sources: list[Path]) -> dict[Path, Path]:
    """relative path -> the newest file with that path across the sources."""
    found: dict[Path, Path] = {}
    for base in sources:
        if _linked(base):
            raise OSError(f"Linked data folder refused: {base}")
        for folder, dirs, names in os.walk(base, followlinks=False):
            here = Path(folder)
            dirs[:] = [d for d in dirs if not _linked(here / d) and not d.startswith(".vault-")
                       and not (here == base and d in SKIP_TOP)]
            for name in names:
                f = here / name
                if name in SKIP_NAMES or name.endswith(".part") or _linked(f):
                    continue
                rel = f.relative_to(base)
                old = found.get(rel)
                if old is None or f.stat().st_mtime > old.stat().st_mtime + MTIME_SLACK:
                    found[rel] = f
    return found


def _digest(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        while chunk := fh.read(8 << 20):
            h.update(chunk)
    return h.hexdigest()


def _starts_with(longer: Path, shorter: Path) -> bool:
    """True when every byte of `shorter` begins `longer` (an append-only log that grew)."""
    n = shorter.stat().st_size
    if n == 0 or longer.stat().st_size <= n:
        return False
    with open(longer, "rb") as a, open(shorter, "rb") as b:
        while n > 0:
            size = min(n, 8 << 20)
            if a.read(size) != b.read(size):
                return False
            n -= size
    return True


def _same_config(a: Path, b: Path, keys: bool = True) -> bool:
    """Two config.json files with the same settings (and, with keys=True, the same AI
    keys): on a drive keys are stored readable, on a computer encrypted, so the bytes
    always differ. keys=False compares settings only."""
    try:
        from cursiv_engine.core import keystore
        x, y = (json.loads(p.read_text(encoding="utf-8")) for p in (a, b))
        if not isinstance(x, dict) or not isinstance(y, dict):
            return False
        if not keys:
            x, y = ({k: v for k, v in d.items() if k not in keystore.SECRET_FIELDS} for d in (x, y))
        return keystore.reveal_all(x) == keystore.reveal_all(y)
    except Exception:
        return False


def keep_drive_keys(config: Path, previous: bytes | None) -> None:
    """After this computer's config.json was copied to a drive without permission to
    copy AI keys: remove this computer's keys and put back exactly the keys the drive
    already had (none, if it had none). Other settings come from this computer."""
    from cursiv_engine.core import atomic, keystore
    data = json.loads(config.read_text(encoding="utf-8"))
    try:
        old = json.loads(previous.decode("utf-8")) if previous else {}
    except ValueError:
        old = {}
    for field in keystore.SECRET_FIELDS:
        data.pop(field, None)
        if isinstance(old, dict) and field in old:
            data[field] = old[field]
    payload = json.dumps(data, indent=2).encode("utf-8")
    atomic.write_bytes(config, payload, protect=False)
    if config.read_bytes() != payload:
        raise OSError("Drive settings read-back verification failed")


def _sealed(p: Path) -> bool:
    """An encrypted store (vault.MAGIC header)."""
    from cursiv_engine.core import vault
    try:
        with open(p, "rb") as fh:
            return fh.read(len(vault.MAGIC)) == vault.MAGIC
    except OSError:
        return False


def _plain(p: Path) -> bytes:
    """A store's readable bytes. Raises VaultError when it is encrypted by a vault
    this process has not unlocked (for example a drive encrypted by an older release)."""
    from cursiv_engine.core import vault
    data = p.read_bytes()
    return vault.reveal(p, data) if data.startswith(vault.MAGIC) else data


def _decide_data(a: bytes, a_time: float, dest: Path, here: str, there: str, suffix: str) -> tuple[str, str]:
    """decide() on readable bytes, for stores that are encrypted on one side."""
    if not dest.exists():
        return "add", f"not on {there}"
    b = _plain(dest)
    if a == b:
        return "same", ""
    if len(a) > len(b) > 0 and a.startswith(b):
        return "update", f"{here} added to it"
    if len(b) > len(a) > 0 and b.startswith(a):
        return "keep", f"{there} added to it"
    both = " (both changed; the other copy is saved in backups)" if suffix == ".jsonl" else ""
    if a_time > dest.stat().st_mtime + MTIME_SLACK:
        return "update", f"newer on {here}{both}"
    return "keep", f"newer on {there}{both}"


def decide(src: Path, dest: Path, here: str = "this computer", there: str = "the drive",
           keys: bool = True) -> tuple[str, str]:
    """`here` names where src lives and `there` where dest lives. keys=False: AI keys
    in config.json are not compared (they are not being copied)."""
    if not dest.exists():
        return "add", f"not on {there}"
    if _sealed(src) or _sealed(dest):
        return _decide_data(_plain(src), src.stat().st_mtime, dest, here, there, src.suffix)
    s, d = src.stat(), dest.stat()
    if s.st_size == d.st_size and _digest(src) == _digest(dest):
        return "same", ""
    if src.name == "config.json" and _same_config(src, dest, keys):
        return "same", ""
    if _starts_with(src, dest):
        return "update", f"{here} added to it"
    if _starts_with(dest, src):
        return "keep", f"{there} added to it"
    both = " (both changed; the other copy is saved in backups)" if src.suffix == ".jsonl" else ""
    if s.st_mtime > d.st_mtime + MTIME_SLACK:
        return "update", f"newer on {here}{both}"
    return "keep", f"newer on {there}{both}"


def plan(sources: list[Path], dest: Path, *, keys: bool = True) -> list[dict]:
    """Read-only. One entry per file: rel, src, dest, action, reason. keys=False when
    AI keys are not being copied: config.json differing only in keys counts as same."""
    from cursiv_engine.core import vault
    if dest.exists() and _linked(dest):
        raise OSError(f"Linked drive data folder refused: {dest}")
    items = []
    for rel, src in sorted(collect(sources).items()):
        target = dest / rel
        for p in (target, *target.parents):
            if p == dest.parent:
                break
            if p.exists() and _linked(p):
                raise OSError(f"Linked drive destination refused: {p}")
        try:
            action, reason = decide(src, target, keys=keys)
        except vault.VaultError as exc:
            action, reason = "skip", f"encrypted and not readable here ({exc}); move it by hand"
        items.append({"rel": rel, "src": src, "dest": target, "action": action, "reason": reason})
    return items


def summary(items: list[dict]) -> dict[str, int]:
    out = {"add": 0, "update": 0, "same": 0, "keep": 0, "skip": 0}
    for it in items:
        out[it["action"]] += 1
    return out


def todo(items: list[dict]) -> list[dict]:
    return [it for it in items if it["action"] in ("add", "update")]


def _write_verified(src: Path, dest: Path, data: bytes | None = None) -> None:
    """Copy src to dest, or write `data` (src's readable bytes) with src's times."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + dest.name, suffix=".part", dir=dest.parent)
    part = Path(tmp)
    try:
        with os.fdopen(fd, "wb") as fo:
            if data is None:
                with open(src, "rb") as fi:
                    shutil.copyfileobj(fi, fo, 8 << 20)
            else:
                fo.write(data)
            fo.flush()
            os.fsync(fo.fileno())
        expected = _digest(src) if data is None else hashlib.sha256(data).hexdigest()
        if _digest(part) != expected:
            raise OSError(f"Copy verification failed: {dest}")
        os.replace(part, dest)
        shutil.copystat(src, dest, follow_symlinks=False)
    finally:
        part.unlink(missing_ok=True)


def apply(items: list[dict], dest: Path, progress=None, cancel: threading.Event | None = None,
          label: str = "usb-update", kept_on: str = "the drive") -> dict:
    """Copy the add/update files. Returns {"copied", "backed_up", "backup"}."""
    work = todo(items)
    backup = dest / "backups" / (label + time.strftime("-%Y%m%d-%H%M%S"))
    report, backed = [], 0
    for i, it in enumerate(work, 1):
        if cancel is not None and cancel.is_set():
            raise InterruptedError
        target: Path = it["dest"]
        if target.exists():
            saved = backup / it["rel"]
            _write_verified(target, saved)
            backed += 1
        # A drive stays readable: an encrypted store from this computer is written decrypted.
        _write_verified(it["src"], target, _plain(it["src"]) if _sealed(it["src"]) else None)
        report.append(f"{it['action']:6}  {it['rel'].as_posix()}  ({it['reason']})")
        if progress:
            progress(int(i * 100 / len(work)), f"Updating your data on the drive: {i} of {len(work)} files")
    if report:
        backup.mkdir(parents=True, exist_ok=True)
        counts = summary(items)
        (backup / "REPORT.txt").write_text(
            f"Cursiv data update ({label}) into {dest}\n"
            f"{counts['add']} added, {counts['update']} updated, {counts['same']} already the same, "
            f"{counts['keep']} kept because the copy on {kept_on} is newer.\n"
            "Replaced drive files are saved in this folder under the same names.\n\n"
            + "\n".join(report) + "\n", encoding="utf-8")
        if backed:
            manifest = {p.relative_to(backup).as_posix(): _digest(p)
                        for p in backup.rglob("*") if p.is_file() and p.name not in ("REPORT.txt", "SHA256.json")}
            (backup / "SHA256.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"copied": len(work), "backed_up": backed, "backup": backup if report else None}


def describe(items: list[dict]) -> str:
    c = summary(items)
    if not items:
        return "No personal data on this computer to copy."
    parts = []
    if c["add"]:
        parts.append(f"{c['add']} new")
    if c["update"]:
        parts.append(f"{c['update']} newer on this computer")
    if c["keep"]:
        parts.append(f"{c['keep']} newer on the drive (kept)")
    parts.append(f"{c['same']} already up to date")
    return "Your data: " + ", ".join(parts) + "."


# ── Drive -> this computer ───────────────────────────────────────────────────
# Work done on a drive comes back in two steps. stage_import() copies the files
# that are new or newer on the drive into ~/.cursiv/import-pending (verified, so
# the drive can be unplugged). The next start of the installed Cursiv calls
# apply_pending_import() before anything reads its data (main.py): each file is
# compared again, replaced files are backed up, keys are encrypted for this
# Windows account. Logins, logs and per-device identity never travel.

PENDING = "import-pending"
# Stores the installed app keeps in ~/.cursiv; everything else lives in APP_DATA.
HOME_STORES = {"conversations", "fieldlog", "documents", "style", "projects", "curiosity", "presence",
               "agents", "family", "plugins", "demo", "space.json", "cursiv_cloud.json"}
IMPORT_SKIP_TOP = {"runtime", "logs"}   # accounts/passwords and logs stay with each computer
IMPORT_SKIP_NAMES = {"portable-layout-v1.json", "field_defaults_applied", "crash.log",
                     "device_key.json", "system.uuid", ".cursiv-private-copy"}


def import_targets() -> tuple[Path, Path]:
    """This computer's (APP_DATA, ~/.cursiv)."""
    from cursiv_engine.core import paths
    return paths.APP_DATA.resolve(), (Path.home() / ".cursiv").resolve()


def _target(rel: Path, app: Path, home: Path) -> Path:
    """Where this computer's Cursiv reads `rel`: the folder that has it (the newer
    one if both do), else the folder that owns that kind of store."""
    a, h = app / rel, home / rel
    if a.exists() and h.exists() and a != h:
        return a if a.stat().st_mtime >= h.stat().st_mtime else h
    if a.exists():
        return a
    if h.exists():
        return h
    return (home if rel.parts[0] in HOME_STORES else app) / rel


def _check_links(target: Path, root: Path) -> None:
    for p in (target, *target.parents):
        if p == root.parent:
            return
        if p.exists() and _linked(p):
            raise OSError(f"Linked data destination refused: {p}")


def _vault_on(*roots: Path) -> bool:
    from cursiv_engine.core import vault
    return any((r / vault.MARKER).exists() for r in roots)


def plan_import(drive_data: Path, app: Path, home: Path) -> list[dict]:
    """Read-only: what bringing the drive's data to this computer would do."""
    from cursiv_engine.core import vault
    drive_locked = _vault_on(drive_data)      # a drive encrypted by an older release
    items = []
    for rel, src in sorted(collect([drive_data]).items()):
        if rel.parts[0] in IMPORT_SKIP_TOP or rel.name in IMPORT_SKIP_NAMES:
            continue
        target = _target(rel, app, home)
        if drive_locked and vault.covered(rel) and _sealed(src):
            items.append({"rel": rel, "src": src, "dest": target, "action": "skip",
                          "reason": "encrypted on the drive; open the drive's Cursiv to read it"})
            continue
        _check_links(target, app if target.is_relative_to(app) else home)
        try:
            action, reason = decide(src, target, "the drive", "this computer")
        except vault.VaultError as exc:
            action, reason = "skip", f"encrypted and not readable here ({exc})"
        items.append({"rel": rel, "src": src, "dest": target, "action": action, "reason": reason})
    return items


def describe_import(items: list[dict]) -> str:
    c = summary(items)
    if not items:
        return "From the drive: nothing to bring to this computer."
    parts = []
    if c["add"]:
        parts.append(f"{c['add']} new")
    if c["update"]:
        parts.append(f"{c['update']} newer on the drive")
    if c["keep"]:
        parts.append(f"{c['keep']} newer on this computer (kept)")
    if c["skip"]:
        parts.append(f"{c['skip']} encrypted (skipped)")
    parts.append(f"{c['same']} already the same")
    return "From the drive to this computer: " + ", ".join(parts) + "."


def pending_dir() -> Path:
    return Path.home() / ".cursiv" / PENDING


def _stage_rel(name: str) -> Path:
    return Path(PENDING) / "files" / name


def _stage_cipher():
    """The unlocked vault key of the folder holding import-pending (~/.cursiv), or None
    when it has no vault."""
    from cursiv_engine.core import vault
    home = pending_dir().parent.absolute()
    return vault._cipher(home) if (home / vault.MARKER).exists() else None


def stage_import(items: list[dict], progress=None, cancel: threading.Event | None = None) -> Path | None:
    """Copy the add/update files to this computer's staging folder. Nothing in
    use is changed until the next start. A newer staging replaces an unapplied one."""
    from cursiv_engine.core import vault
    work = todo(items)
    if not work:
        return None
    stage = pending_dir()
    tmp = stage.with_name(PENDING + ".tmp-" + time.strftime("%Y%m%d%H%M%S"))
    entries = []
    try:
        for i, it in enumerate(work):
            if cancel is not None and cancel.is_set():
                raise InterruptedError
            name = f"{i:05d}"
            # Conversations and memories waiting here are encrypted like the stores they join.
            cipher = _stage_cipher() if vault.covered(it["rel"]) else None
            sealed = vault.pack(cipher, _stage_rel(name), it["src"].read_bytes()) if cipher else None
            _write_verified(it["src"], tmp / "files" / name, sealed)
            entries.append({"file": name, "target": str(it["dest"]), "rel": it["rel"].as_posix(),
                            "action": it["action"], "reason": it["reason"], "sealed": bool(cipher),
                            "sha256": _digest(tmp / "files" / name)})
            if progress:
                progress(int((i + 1) * 100 / len(work)), f"Copying from the drive: {i + 1} of {len(work)} files")
        (tmp / "manifest.json").write_text(json.dumps(entries, indent=2), encoding="utf-8")
        if stage.exists():
            shutil.rmtree(stage)
        os.replace(tmp, stage)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
    return stage


def apply_pending_import() -> dict | None:
    """Installed app, at startup before data is read. None when nothing is staged."""
    stage = pending_dir()
    manifest = stage / "manifest.json"
    if not manifest.exists():
        return None
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    app, home = import_targets()
    stamp = time.strftime("usb-import-%Y%m%d-%H%M%S")
    report, applied, backed = [], 0, 0
    for e in entries:
        staged, target, rel = stage / "files" / e["file"], Path(e["target"]), Path(e["rel"])
        root = next((r for r in (app, home) if target.resolve().is_relative_to(r)), None)
        if root is None or not staged.is_file() or _digest(staged) != e["sha256"]:
            report.append(f"skipped  {e['rel']}  (staged copy missing, damaged or outside Cursiv's data)")
            continue
        _check_links(target, root)
        from cursiv_engine.core import atomic, vault
        data = staged.read_bytes()
        if e.get("sealed"):
            data = vault.unpack(_stage_cipher(), _stage_rel(e["file"]), data)
        into_vault = vault.owner(target) is not None
        if e.get("sealed") or into_vault:
            action, reason = _decide_data(data, staged.stat().st_mtime, target, "the drive",
                                          "this computer", target.suffix)
        else:
            action, reason = decide(staged, target, "the drive", "this computer")
        if action not in ("add", "update"):
            report.append(f"kept     {e['rel']}  ({reason or 'already the same'})")
            continue
        if target.exists():
            _write_verified(target, root / "backups" / stamp / rel)   # stays encrypted if it was
            backed += 1
        if into_vault:
            atomic.write_bytes(target, data)                          # encrypted for this computer
            if _plain(target) != data:
                raise OSError(f"Encrypted import read-back verification failed: {target}")
            mtime = staged.stat().st_mtime
            os.utime(target, (mtime, mtime))
        else:
            _write_verified(staged, target, data if e.get("sealed") else None)
        if target.name == "config.json":
            from cursiv_engine.core import keystore
            keystore.migrate(target)          # readable drive keys -> encrypted for this account
        applied += 1
        report.append(f"{action:8} {e['rel']}  ({reason})")
    out = home / "backups" / stamp
    out.mkdir(parents=True, exist_ok=True)
    (out / "REPORT.txt").write_text(
        f"Cursiv data brought from a drive\n{applied} file(s) applied, {backed} replaced file(s) "
        f"saved under backups/{stamp} in the folder they came from.\n\n" + "\n".join(report) + "\n",
        encoding="utf-8")
    shutil.rmtree(stage)
    return {"applied": applied, "backed_up": backed, "report": out / "REPORT.txt"}
