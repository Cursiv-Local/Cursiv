"""Bounded local traversal through the existing workspace authorization layer."""
import os
from pathlib import Path
import re
import time


def search(folder, args, root):
    from . import file_access as fs
    pattern = args.get('pattern', '*')
    needle, imports = args.get('contains'), args.get('imports')
    counts = args.get('line_counts', False)
    terms = args.get('terms')
    if terms is not None and (not isinstance(terms, list) or not 1 <= len(terms) <= 5 or
                              any(not isinstance(t, str) or not 1 <= len(t) <= 120 for t in terms)):
        raise ValueError('Content terms must be a short list of literal strings')
    if not isinstance(pattern, str) or '..' in Path(pattern).parts or Path(pattern).is_absolute():
        raise ValueError('Search pattern must stay inside the workspace')
    if needle is not None and (not isinstance(needle, str) or not 1 <= len(needle) <= 500):
        raise ValueError('Search text needs 1–500 literal characters')
    if imports is not None and (not isinstance(imports, str) or not re.fullmatch(r'[\w.]{1,120}', imports)):
        raise ValueError('Import search needs a module name')
    if type(counts) is not bool:
        raise ValueError('line_counts must be a boolean')
    rows, scanned, size, output = [], 0, 0, 0
    started, limited = time.monotonic(), False
    import_re = (re.compile(r'^\s*(?:from\s+' + re.escape(imports) + r'(?:\b|\.)|import\s+[^#\n]*\b'
                            + re.escape(imports) + r'\b)') if imports else None)
    for current, dirs, files in os.walk(folder, followlinks=False):
        safe_dirs = []
        for directory in sorted(dirs):
            try:
                fs.resolve(str(Path(current) / directory), root)
                safe_dirs.append(directory)
            except (OSError, ValueError):
                pass
        dirs[:] = safe_dirs
        for item in sorted(files + ([] if needle is not None or imports or counts or terms else dirs)):
            if time.monotonic() - started > 3 or scanned >= 3000 or size >= 8_000_000:
                limited = True
                break
            child = Path(current) / item
            relative = child.relative_to(folder)
            if not (relative.match(pattern) or (pattern.startswith('**/') and relative.match(pattern[3:]))):
                continue
            try:
                path = fs.resolve(str(child), root)
                scanned += 1
                if needle is not None or imports or counts or terms:
                    if not path.is_file() or path.stat().st_size > fs.MAX_BYTES:
                        continue
                    raw = path.read_bytes()
                    size += len(raw)
                    text = fs._decode_text(raw)  # never expose a credential-containing file
                    lines = text.splitlines()
                    found = ([f'{path}: {len(lines)} lines'] if counts else
                             (f'{path}:{n}: {line[:300]}' for n, line in enumerate(lines, 1)
                              if (needle is not None and needle in line) or (import_re and import_re.search(line)) or
                              (terms and any(t.casefold() in line.casefold() for t in terms))))
                else:
                    found = [str(path)]
            except (OSError, ValueError, UnicodeError):
                continue
            for row in found:
                if len(rows) >= 80 or output + len(row) > 12000:
                    limited = True
                    break
                rows.append(row)
                output += len(row)
            if limited:
                break
        if limited:
            break
        if '**' not in pattern:
            dirs[:] = []
    return fs.FileResult('search_files', str(folder), entries=rows, truncated=limited)
