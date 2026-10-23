---
title: Automation script — organize a folder by file type (safe dry run first)
triggers: organi[sz]e|sort files|rename files|downloads folder|automat|batch rename|move files|clean ?up (my )?folder
---
## Question
Write a script that sorts my Downloads folder into subfolders by file type.

## Answer
**Where:** PowerShell on Windows. No packages needed — only Python's standard library.

### The program
Save as `organize.py` anywhere (e.g. `$HOME\projects\organize\organize.py`):
```python
"""Sort files in a folder into subfolders by type. Dry run by default."""
import argparse
import shutil
from pathlib import Path

GROUPS = {
    "Images":    {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp"},
    "Documents": {".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv", ".md"},
    "Audio":     {".mp3", ".wav", ".m4a", ".flac"},
    "Video":     {".mp4", ".mov", ".mkv", ".avi"},
    "Archives":  {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Installers": {".exe", ".msi"},
}


def group_for(path: Path) -> str:
    ext = path.suffix.lower()
    return next((name for name, exts in GROUPS.items() if ext in exts), "Other")


def unique_target(target: Path) -> Path:
    n = 1
    while target.exists():
        target = target.with_name(f"{target.stem} ({n}){target.suffix}")
        n += 1
    return target


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="?", default=str(Path.home() / "Downloads"))
    ap.add_argument("--go", action="store_true", help="actually move files (default: just show)")
    args = ap.parse_args()

    folder = Path(args.folder)
    files = [f for f in folder.iterdir() if f.is_file()]
    for f in files:
        dest_dir = folder / group_for(f)
        target = unique_target(dest_dir / f.name)
        print(f"{'MOVE' if args.go else 'would move'}: {f.name} -> {dest_dir.name}/")
        if args.go:
            dest_dir.mkdir(exist_ok=True)
            shutil.move(str(f), str(target))
    print(f"{len(files)} file(s) {'moved' if args.go else 'checked (dry run — add --go to move)'}")


if __name__ == "__main__":
    main()
```

### Run it
1. Go to the folder with the script:
```powershell
cd $HOME\projects\organize
```
2. **Preview first** (moves nothing):
```powershell
py organize.py
```
3. If the list looks right, do it for real:
```powershell
py organize.py --go
```
Another folder: `py organize.py "D:\Photos" --go`.

### If something goes wrong
- `PermissionError` → a file is open in another program; close it and run again.
- Files you don't want moved → add their extensions to a group, or delete the "Other" handling.
- Same name twice → the script adds `(1)`, `(2)` instead of overwriting.
