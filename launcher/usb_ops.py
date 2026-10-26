"""USB kit operations.

build_plan/update_plan prepare copy plans; copy_files stages each file atomically;
make_usb orchestrates an explicit kit request; verify_usb checks copied files.
The UsbRuntime parameter supplies paths, configuration and existing callbacks.
Widgets and private-copy choices remain in usb_maker.
"""
from __future__ import annotations
from pathlib import Path
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from usb_maker import _Signals

from usb_ops_runtime import UsbRuntime
import usb_sync

def program_dir(runtime: UsbRuntime) -> Path | None:
    """The built Cursiv folder to copy (the running app, or dist\\Cursiv in a dev checkout)."""
    if getattr(runtime.sys, "frozen", False):
        return runtime.Path(runtime.sys.executable).resolve().parent
    dev = runtime.Path(runtime.__file__).resolve().parent.parent / "dist" / "Cursiv"
    return dev if (dev / "Cursiv.exe").exists() else None

def models_dir(runtime: UsbRuntime) -> Path:
    return runtime.Path(runtime.os.environ.get("OLLAMA_MODELS") or (runtime.Path.home() / ".ollama" / "models"))

def ollama_dir(runtime: UsbRuntime) -> Path | None:
    exe = runtime.shutil.which("ollama")
    if exe:
        return runtime.Path(exe).resolve().parent
    d = runtime.Path(runtime.os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama"
    return d if (d / "ollama.exe").exists() else None

def list_models(runtime: UsbRuntime) -> list[dict]:
    """Every pulled Ollama model: name, manifest path, blob files and total size."""
    base = runtime.models_dir()
    mroot = base / "manifests"
    out = []
    if not mroot.is_dir():
        return out
    for mf in mroot.rglob("*"):
        if not mf.is_file():
            continue
        try:
            data = runtime.json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            continue
        digests = [l.get("digest", "") for l in data.get("layers", [])]
        digests.append((data.get("config") or {}).get("digest", ""))
        blobs = [base / "blobs" / d.replace(":", "-") for d in digests if d]
        blobs = [b for b in blobs if b.exists()]
        parts = mf.relative_to(mroot).parts          # registry / namespace / name / tag
        name = f"{parts[-2]}:{parts[-1]}" if len(parts) >= 2 else mf.name
        if len(parts) >= 3 and parts[-3] != "library":
            name = f"{parts[-3]}/{name}"
        out.append({"name": name, "manifest": mf, "blobs": blobs,
                    "size": sum(b.stat().st_size for b in blobs)})
    return sorted(out, key=lambda m: m["name"])

def model_license(runtime: UsbRuntime, model: dict) -> str:
    """The license text Ollama stored with this model ("" if it has none)."""
    try:
        data = runtime.json.loads(runtime.Path(model["manifest"]).read_text(encoding="utf-8"))
    except Exception:
        return ""
    parts = []
    for layer in data.get("layers", []):
        if layer.get("mediaType") == runtime._LICENSE_LAYER and layer.get("digest"):
            blob = runtime.models_dir() / "blobs" / layer["digest"].replace(":", "-")
            try:
                parts.append(blob.read_text(encoding="utf-8", errors="replace").strip())
            except OSError:
                pass
    return "\n\n".join(p for p in parts if p)

def _safe_name(runtime: UsbRuntime, name: str) -> str:
    return "".join(c if c.isalnum() or c in "-._" else "_" for c in name)

def write_licenses(runtime: UsbRuntime, root: Path, models: list[dict]) -> list[str]:
    """Licenses/ on the drive: Cursiv, Ollama, and one file per model. Returns the
    names of models that came without a license (said so in the index)."""
    folder = root / "Licenses"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.txt"):
        old.unlink(missing_ok=True)          # models removed from the drive drop out
    for name in ("Cursiv-LICENSE.txt", "Ollama-LICENSE.txt"):
        src = runtime._BUNDLED_LICENSES / name
        if src.exists():
            runtime.shutil.copyfile(src, folder / name)
    lines = ["Licenses for what's on this drive", "=================================", "",
             "Cursiv: MIT (Cursiv-LICENSE.txt)", "Ollama, the AI engine: MIT (Ollama-LICENSE.txt)", "",
             "AI models (each file is the license the model came with):"]
    missing = []
    for m in sorted(models, key=lambda m: m["name"]):
        text = runtime.model_license(m)
        family = m["name"].split(":")[0].split("/")[-1]
        extra = next((v for k, v in runtime._EXTRA_TERMS.items() if family.startswith(k)), "")
        if text:
            fname = f"model-{runtime._safe_name(m['name'])}.txt"
            (folder / fname).write_text(text + (f"\n\n{extra}\n" if extra else "\n"), encoding="utf-8")
            lines.append(f"  {m['name']}: {fname}")
        else:
            missing.append(m["name"])
            lines.append(f"  {m['name']}: no license came with this model -- check its page before sharing")
        if extra:
            lines.append(f"    {extra}")
    lines += ["", "Details: MODELS.md at https://github.com/winklersllc2026-bit/Cursiv"]
    (folder / "README.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return missing

def required_names(runtime: UsbRuntime, models: list[dict]) -> list[str]:
    names = {m["name"] for m in models}
    chat = next((n for n in runtime.REQUIRED_CHAT if n in names), runtime.REQUIRED_CHAT[0])
    return [chat, runtime.REQUIRED_EMBED]

def pull_model(runtime: UsbRuntime, tag: str, sig, cancel: threading.Event) -> None:
    """Download a model into this computer's Ollama so it can be copied."""
    from cursiv_engine.core import netgate
    netgate.require(f"Downloading {tag}")
    req = runtime.urllib.request.Request(f"{runtime.OLLAMA_API}/api/pull",
                                 data=runtime.json.dumps({"name": tag, "stream": True}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        r = runtime.urllib.request.urlopen(req, timeout=3600)
    except Exception:
        raise RuntimeError(f"{tag} isn't downloaded yet and Ollama isn't running to fetch it. "
                           "Open Setup, start Ollama, then try again.")
    with r:
        for line in r:
            if cancel.is_set():
                raise InterruptedError
            try:
                st = runtime.json.loads(line.decode())
            except Exception:
                continue
            if st.get("error"):
                raise RuntimeError(f"Downloading {tag} failed: {st['error']}")
            total, done = st.get("total") or 0, st.get("completed") or 0
            if total and done:
                sig.progress.emit(int(done * 100 / total),
                                  f"Downloading {tag} first… {done / 1e9:.2f} of {total / 1e9:.2f} GB")
            if st.get("status") == "success":
                return
    raise RuntimeError(f"Downloading {tag} ended early — try again.")

def _volume_info(runtime: UsbRuntime, root: str) -> tuple[str, str]:
    label = runtime.ctypes.create_unicode_buffer(261)
    fs = runtime.ctypes.create_unicode_buffer(261)
    ok = runtime.ctypes.windll.kernel32.GetVolumeInformationW(
        runtime.ctypes.c_wchar_p(root), label, 261, None, None, None, fs, 261)
    return (label.value, fs.value) if ok else ("", "")

def list_drives(runtime: UsbRuntime) -> list[dict]:
    """Removable drives plus external fixed drives (USB SSDs report as fixed).
    Never the Windows drive."""
    drives = []
    if runtime.sys.platform != "win32":
        return drives
    system = runtime.os.environ.get("SystemDrive", "C:").upper()[:1]
    mask = runtime.ctypes.windll.kernel32.GetLogicalDrives()
    for i, letter in enumerate(runtime.string.ascii_uppercase):
        if not mask & (1 << i) or letter == system:
            continue
        root = f"{letter}:\\"
        kind = runtime.ctypes.windll.kernel32.GetDriveTypeW(runtime.ctypes.c_wchar_p(root))
        if kind not in (2, 3):                 # 2 = removable, 3 = fixed
            continue
        try:
            usage = runtime.shutil.disk_usage(root)
        except Exception:
            continue                           # empty card reader etc.
        label, fs = runtime._volume_info(root)
        drives.append({"root": root, "letter": letter, "label": label, "fs": fs.upper(),
                       "removable": kind == 2, "free": usage.free, "total": usage.total})
    return drives

def _program_files(runtime: UsbRuntime, src: Path, include_private: bool) -> list[tuple[Path, Path]]:
    skip_top = {"unins000.dat", "unins000.exe"}
    pairs = []
    for f in src.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(src)
        if f.name == '.vault-lease':
            continue  # live OS lease is process state, never portable data
        top = rel.parts[0]
        if top in skip_top or ".bak" in top:   # installer leftovers, old-version backups
            continue
        if any(part.startswith(".cursiv") for part in rel.parts):
            continue  # personal data goes to Home\.cursiv (usb_sync), never into the program folder
        pairs.append((f, runtime.Path("Cursiv") / rel))
    return pairs

def build_plan(runtime: UsbRuntime, models: list[dict], include_private: bool, ollama_src: Path | None) -> list[tuple[Path, Path]]:
    prog = runtime.program_dir()
    if prog is None:
        raise RuntimeError("Couldn't find the Cursiv program files to copy.")
    pairs = runtime._program_files(prog, include_private)
    if ollama_src:
        for f in ollama_src.rglob("*"):
            if f.is_file() and not f.name.lower().startswith("unins"):
                pairs.append((f, runtime.Path("Ollama") / f.relative_to(ollama_src)))
    mbase = runtime.models_dir()
    seen = set()
    for m in models:
        for f in [m["manifest"], *m["blobs"]]:
            if f not in seen:
                seen.add(f)
                pairs.append((f, runtime.Path("Models") / f.relative_to(mbase)))
    return pairs

def _needs_copy(runtime: UsbRuntime, src: Path, dest: Path) -> bool:
    """Copy unless the drive already has this exact file (same size and time --
    copies keep the source's modified time, so a rebuilt file of the same size
    still differs)."""
    try:
        s, d = src.stat(), dest.stat()
    except Exception:
        return True
    return s.st_size != d.st_size or abs(s.st_mtime - d.st_mtime) > runtime.MTIME_SLACK

def _is_personal(runtime: UsbRuntime, rel: Path) -> bool:
    # .cursiv and older copies of it such as .cursiv.moved-<date> are data, never pruned
    return any(part.startswith(".cursiv") for part in rel.parts) or rel.name == "portable.cursiv"

def stale_files(runtime: UsbRuntime, root: Path, plan: list[tuple[Path, Path]]) -> list[Path]:
    """Files in the drive's program folders that the current build doesn't have
    (e.g. a library a newer Cursiv dropped). Never personal data."""
    wanted = {d.resolve() for _s, d in plan}
    out = []
    for top in runtime.PRUNED_DIRS:
        base = root / top
        if not base.is_dir():
            continue
        if base.is_symlink() or base.is_junction():
            raise OSError(f'Linked USB program folder refused: {base}')
        for folder, dirs, names in runtime.os.walk(base, followlinks=False):
            dirs[:] = [name for name in dirs if not runtime._is_personal((runtime.Path(folder) / name).relative_to(root))
                       and not (runtime.Path(folder) / name).is_symlink() and not (runtime.Path(folder) / name).is_junction()]
            for name in names:
                f = runtime.Path(folder) / name
                if not f.is_symlink() and f.resolve() not in wanted and not runtime._is_personal(f.relative_to(root)):
                    out.append(f)
    return out

def verify_usb(runtime: UsbRuntime, plan: list[tuple[Path, Path]]) -> list[str]:
    """Every planned file is on the drive with the right size and time.
    Returns the problems (empty list = the drive matches the build)."""
    problems = []
    for src, dest in plan:
        if not dest.exists():
            problems.append(f"missing: {dest}")
        elif runtime._needs_copy(src, dest):
            problems.append(f"different: {dest}")
    return problems

def copy_files(runtime: UsbRuntime, todo: list[tuple[Path, Path]], progress, cancel: threading.Event) -> None:
    """Copy each file to a .part file, flush it to disk, then rename it into
    place -- an interrupted copy never leaves a half-written file behind."""
    total = sum(s.stat().st_size for s, _ in todo) or 1
    copied = 0
    for i, (src, dest) in enumerate(todo, 1):
        from cursiv_engine.core.state_store import checked
        checked(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = runtime.tempfile.mkstemp(prefix='.' + dest.name, suffix='.part', dir=dest.parent)
        part = runtime.Path(temporary)
        try:
            with runtime.os.fdopen(fd, 'wb') as fo, open(src, 'rb') as fi:
                while chunk := fi.read(8 << 20):
                    if cancel.is_set():
                        raise InterruptedError
                    fo.write(chunk)
                    copied += len(chunk)
                    progress(int(copied * 100 / total),
                             f"Copying {i} of {len(todo)} files — {copied / runtime.GB:.1f} of {total / runtime.GB:.1f} GB")
                fo.flush()
                runtime.os.fsync(fo.fileno())
            checked(dest)
            runtime.os.replace(part, dest)
            runtime.shutil.copystat(src, dest, follow_symlinks=False)
        finally:
            part.unlink(missing_ok=True)

def _download_ollama(runtime: UsbRuntime, dest_dir: Path, progress, cancel: threading.Event) -> Path:
    """Download Ollama's Windows zip from its latest GitHub release and check it
    against the SHA-256 GitHub publishes for that file. Returns the unpacked folder."""
    import hashlib
    api = runtime.urllib.request.Request("https://api.github.com/repos/ollama/ollama/releases/latest",
                                 headers={"User-Agent": "Cursiv-USB"})
    with runtime.urllib.request.urlopen(api, timeout=30) as r:
        release = runtime.json.loads(r.read())
    asset = next((a for a in release.get("assets", []) if a.get("name") == "ollama-windows-amd64.zip"), None)
    digest = (asset or {}).get("digest", "")
    if not asset or not digest.startswith("sha256:"):
        raise RuntimeError("Couldn't find a checksum for the Ollama download, so it wasn't used. "
                           "Install Ollama on this computer (Setup window) and try again.")
    zpath = dest_dir / "ollama.zip"
    sha = hashlib.sha256()
    req = runtime.urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": "Cursiv-USB"})
    with runtime.urllib.request.urlopen(req, timeout=60) as r, open(zpath, "wb") as out:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        while chunk := r.read(1 << 20):
            if cancel.is_set():
                raise InterruptedError
            out.write(chunk)
            sha.update(chunk)
            got += len(chunk)
            progress(int(got * 100 / total) if total else -1,
                     f"Downloading Ollama… {got >> 20} MB" + (f" of {total >> 20} MB" if total else ""))
    if "sha256:" + sha.hexdigest() != digest:
        zpath.unlink(missing_ok=True)
        raise RuntimeError("The Ollama download didn't match its published checksum, so it wasn't used. Try again.")
    out_dir = dest_dir / "ollama"
    with runtime.zipfile.ZipFile(zpath) as z:
        z.extractall(out_dir)
    return out_dir

def _own_notebook(items: list[dict]) -> list[dict]:
    """A drive named for one person (U103) starts its own field notebook and signing key: this computer's
    notebook and key aren't copied onto it (whose work it carries is chosen separately)."""
    return [it for it in items if it["rel"].parts[0] != "fieldlog" and it["rel"].name != "device_key.json"]


def make_usb(runtime: UsbRuntime, root: Path, models: list[dict], include_private: bool, sig: _Signals, cancel: threading.Event, field: bool,
             include_keys: bool = False, workspace_name: str = "", team_ids: list[str] | tuple = ()) -> None:
    try:
        if workspace_name:
            from cursiv_engine.core import fieldlog
            workspace_name = fieldlog.clean_name(workspace_name)
        have = {m["name"] for m in runtime.list_models()}
        for tag in runtime.required_names(runtime.list_models()):
            if tag not in have:
                runtime.pull_model(tag, sig, cancel)
        chosen = {m["name"] for m in models} | set(runtime.required_names(runtime.list_models()))
        models = [m for m in runtime.list_models() if m["name"] in chosen]

        osrc = runtime.ollama_dir()
        tmp_zip_dir = None
        if osrc is None:
            sig.progress.emit(-1, "Downloading the Ollama engine (about 1-2 GB)…")
            tmp_zip_dir = runtime.Path(runtime.tempfile.mkdtemp(prefix="cursiv_ollama_"))
            osrc = runtime._download_ollama(tmp_zip_dir, sig.progress.emit, cancel)

        # Program files only; personal data is compared and updated separately
        # below (usb_sync), so drive data that is newer is never overwritten.
        plan = runtime.update_plan(root, runtime.build_plan(models, include_private, osrc))
        todo = [(s, d) for s, d in plan if runtime._needs_copy(s, d)]
        data_dir = root / "Home" / ".cursiv"
        data_items = usb_sync.plan(usb_sync.data_sources(), data_dir, keys=include_keys) if include_private else []
        if workspace_name:
            data_items = _own_notebook(data_items)
        total = (sum(s.stat().st_size for s, _ in todo)
                 + sum(it["src"].stat().st_size for it in usb_sync.todo(data_items))) or 1

        _, fs = runtime._volume_info(str(root))
        if fs.upper() == "FAT32" and any(s.stat().st_size > runtime.FAT32_MAX for s, _ in todo):
            raise RuntimeError("This drive is formatted FAT32, which can't hold files over 4 GB "
                               "(some AI models are bigger). Reformat it as exFAT and try again.")
        free = runtime.shutil.disk_usage(str(root)).free
        if total > free:
            raise RuntimeError(f"Not enough space: needs {total / runtime.GB:.1f} GB, the drive has "
                               f"{free / runtime.GB:.1f} GB free. Untick some models and try again.")

        runtime.copy_files(todo, sig.progress.emit, cancel)
        for f in runtime.stale_files(root, plan):
            f.unlink(missing_ok=True)

        sig.progress.emit(-1, "Checking the drive matches…")
        problems = runtime.verify_usb(plan)
        if problems:
            raise RuntimeError(f"{len(problems)} file(s) didn't copy correctly (first: {problems[0]}). "
                               "Click Make USB again to fix them.")

        data_note = ""
        if include_private:
            data_dir.mkdir(parents=True, exist_ok=True)
            # Data an older USB maker left in the program folder joins Home first,
            # so the drive never starts with two versions of the same store.
            import portable
            portable.migrate_data(root, data_dir)
            data_items = usb_sync.plan(usb_sync.data_sources(), data_dir, keys=include_keys)
            if workspace_name:
                data_items = _own_notebook(data_items)
            config = data_dir / "config.json"
            previous = config.read_bytes() if config.is_file() else None
            result = usb_sync.apply(data_items, data_dir, sig.progress.emit, cancel)
            counts = usb_sync.summary(data_items)
            data_note = (f" Your data: {counts['add']} new and {counts['update']} updated file(s) copied, "
                         f"{counts['keep']} newer on the drive kept.")
            if result["backup"]:
                data_note += f" Replaced drive files were saved in {result['backup']}."
            (root / runtime.PRIVATE_MARKER).parent.mkdir(parents=True, exist_ok=True)
            (root / runtime.PRIVATE_MARKER).write_text(
                "This drive holds private Cursiv data. Program updates preserve it.\n", encoding="utf-8")
            # AI keys are personal. They are copied only with the separate opt-in, and
            # then readable (the USB runs on other PCs, where this account's encryption
            # can't be undone). Without it the drive keeps exactly the keys it had.
            if any(it["rel"] == runtime.Path("config.json") for it in usb_sync.todo(data_items)):
                if include_keys:
                    from cursiv_engine.core import keystore
                    keystore.export_readable(config)
                else:
                    usb_sync.keep_drive_keys(config, previous)
            data_note += (" Your AI keys were copied and are readable on this drive." if include_keys
                          else " Your AI keys were not copied.")

        if workspace_name or team_ids:
            # Whose drive this is, and whose work it carries (U103). The drive's own notebook keeps its id if
            # it already has one, so a re-made drive is still the same person's.
            from cursiv_engine.core import fieldlog, fieldsync
            notebook = data_dir / "fieldlog"
            if workspace_name:
                me = fieldlog.name_new_notebook(notebook, workspace_name)
                data_note += f" Its field notebook is {me['name']}'s."
            if team_ids:
                sig.progress.emit(-1, "Copying the chosen team notebooks…")
                copied = fieldsync.copy_notebooks_to(notebook, list(team_ids))
                names = fieldlog.notebook_names()
                data_note += (" Team notebooks on it: " + ", ".join(fieldlog.who(i, names) for i in copied) + ".")

        runtime.write_licenses(root, models)

        (root / "Cursiv" / "portable.cursiv").write_text(
            "This copy of Cursiv runs from this drive. See README.txt.\n", encoding="utf-8")
        field_marker = root / "Cursiv" / "field.cursiv"
        if field:
            field_marker.write_text("Field copy: on first start, offline mode on, break notes off, "
                                    "learning off (portable.apply_field_defaults).\n", encoding="utf-8")
        else:
            field_marker.unlink(missing_ok=True)
        (root / "Home").mkdir(exist_ok=True)
        (root / "Start Cursiv.bat").write_bytes(runtime.START_BAT.encode("ascii"))
        (root / "README.txt").write_text(runtime.README, encoding="utf-8")
        runtime.tidy_root(root)
        if tmp_zip_dir:
            runtime.shutil.rmtree(tmp_zip_dir, ignore_errors=True)
        note = data_note + ' Private data on this drive is not encrypted by Cursiv.'
        sig.done.emit(True, f"Done. Plug the drive into any Windows PC and double-click "
                            f"\"Start Cursiv\".{note}")
    except InterruptedError:
        sig.done.emit(False, "Stopped. Click Make USB again to pick up where it left off.")
    except Exception as exc:
        sig.done.emit(False, f"Couldn't finish: {exc}")

def check_usb(runtime: UsbRuntime, root: Path, models: list[dict], include_private: bool,
              include_keys: bool = False) -> tuple[bool, str]:
    """Read every file the drive should have and say what an update would change.
    Writes nothing. Returns (up_to_date, report)."""
    lines = []
    made = (root / "Cursiv" / "portable.cursiv").exists()
    lines.append("Cursiv is on this drive." if made else "This drive doesn't have Cursiv yet.")
    have = {m["name"] for m in runtime.list_models()}
    missing_models = [t for t in runtime.required_names(runtime.list_models()) if t not in have]
    osrc = runtime.ollama_dir()
    plan = runtime.update_plan(root, runtime.build_plan(models, False, osrc))
    todo = [(s, d) for s, d in plan if runtime._needs_copy(s, d)]
    groups: dict[str, list[int]] = {}
    for s, d in todo:
        g = groups.setdefault(d.relative_to(root.resolve()).parts[0], [0, 0])
        g[0] += 1
        g[1] += s.stat().st_size
    names = {"Cursiv": "Program", "Ollama": "AI engine", "Models": "AI models"}
    for top in ("Cursiv", "Ollama", "Models"):
        if top in groups:
            n, size = groups[top]
            lines.append(f"{names[top]}: {n} file(s) to copy ({size / runtime.GB:.2f} GB).")
        else:
            lines.append(f"{names[top]}: up to date.")
    stale = runtime.stale_files(root, plan)
    if stale:
        lines.append(f"{len(stale)} old program file(s) the current version no longer uses would be removed.")
    if missing_models:
        lines.append("Needs downloading first: " + ", ".join(missing_models) + ".")
    if osrc is None:
        lines.append("The Ollama engine isn't on this computer; it would be downloaded.")
    bat = root / "Start Cursiv.bat"
    bat_ok = bat.exists() and bat.read_bytes() == runtime.START_BAT.encode("ascii")
    if not bat_ok:
        lines.append("Start Cursiv.bat is missing or out of date.")
    data_dir = root / "Home" / ".cursiv"
    legacy = [p for p in (root / "Cursiv" / "_internal" / ".cursiv", root / "Cursiv" / ".cursiv") if p.is_dir()]
    pending_migration = bool(legacy) and not (data_dir / "portable-layout-v1.json").exists()
    if pending_migration:
        lines.append("Older data in the program folder will be moved into Home\\.cursiv "
                     "(the newer copy of each file is kept; replaced files are backed up).")
    data_todo = []
    if include_private:
        items = usb_sync.plan(usb_sync.data_sources(), data_dir, keys=include_keys)
        data_todo = usb_sync.todo(items)
        lines.append(usb_sync.describe(items))
        if runtime.os.environ.get("CURSIV_PORTABLE") != "1" and data_dir.is_dir():
            back = usb_sync.plan_import(data_dir, *usb_sync.import_targets())
            lines.append(usb_sync.describe_import(back)
                         + (" Use \"Bring drive data here\" for those." if usb_sync.todo(back) else ""))
    else:
        lines.append("Your data: not checked (tick \"Include my memories…\" to compare it).")
    up_to_date = (made and not todo and not stale and not missing_models and osrc is not None
                  and bat_ok and not pending_migration and not data_todo)
    lines.append("Nothing to update." if up_to_date else "Click Update USB to bring the drive up to date.")
    return up_to_date, "\n".join(lines)


def update_plan(runtime: UsbRuntime, root: Path, pairs: list[tuple[Path, Path]]) -> list[tuple[Path, Path]]:
    """Never overwrite a private file during a program refresh."""
    root = root.resolve()
    result = []
    for source, relative in pairs:
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('USB copy path must be relative and inside the drive')
        target = root / relative
        cursor = target
        while cursor != root:
            if cursor.is_symlink() or cursor.is_junction():
                raise OSError(f'USB update refuses linked destination: {cursor}')
            cursor = cursor.parent
        if not target.resolve().is_relative_to(root):
            raise OSError('USB destination escapes selected drive')
        if '.cursiv' in relative.parts and target.exists():
            continue
        result.append((source, target))
    return result

def tidy_root(runtime: UsbRuntime, root: Path) -> None:
    """The drive's top level shows only Start Cursiv.bat, README.txt and the folders.
    The drive icon stays inside the Cursiv folder; autorun.inf (the drive's name and
    icon in File Explorer) is hidden. Older USBs had a cursiv.ico at the top: removed."""
    (root / "cursiv.ico").unlink(missing_ok=True)
    ico = next((root / "Cursiv").rglob("cursiv.ico"), None)
    inf = root / "autorun.inf"
    try:
        if inf.exists():
            runtime.ctypes.windll.kernel32.SetFileAttributesW(str(inf), 0x80)     # normal, so it can be rewritten
        if ico:
            rel = str(ico.relative_to(root)).replace("/", "\\")
            inf.write_text(f"[autorun]\r\nlabel=Cursiv\r\nicon={rel}\r\n", encoding="utf-8")
            runtime.ctypes.windll.kernel32.SetFileAttributesW(str(inf), 0x02)     # hidden
    except Exception:
        pass
