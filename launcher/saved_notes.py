"""Read-only presentation helpers for the existing saved-note archive."""
from __future__ import annotations

from datetime import datetime
import json
import math
from pathlib import Path


def read_notes() -> tuple[list[dict], list[str]]:
    from cursiv_engine.core import strand_store
    path = strand_store.STRANDS_FILE
    try:
        stream = path.open(encoding='utf-8')
    except FileNotFoundError:
        from cursiv_engine.core.paths import portable_root
        root = portable_root()
        if root and not root.exists():
            raise OSError('Portable storage is unavailable')
        return [], []
    records, warnings = [], []
    with stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError('Not a note record')
                records.append(record)
            except ValueError:
                warnings.append(f'Line {number} could not be displayed. The archive was not changed.')
    return records, warnings


def category(record: dict) -> str:
    return str(record.get('territory_tag', 'general'))


def content(record: dict) -> tuple[str, str, str]:
    """Decode the preserved payload; summary columns in older records are shortened."""
    query, answer, warning = str(record.get('query', '')), str(record.get('synthesis', '')), ''
    if record.get('strand'):
        try:
            from cursiv_engine.core.strand import decode
            decoded = decode(record['strand'])
            if isinstance(decoded, dict):
                query = str(decoded.get('query', query))
                answer = str(decoded.get('synthesis', answer))
            elif isinstance(decoded, str):
                answer = decoded
        except Exception:
            warning = 'The original encoded content could not be decoded. Showing the available stored text.'
    return query, answer, warning


def full_text(record: dict) -> str:
    query, answer, warning = content(record)
    text = ('Question\n' + query + '\n\nSaved note\n' + answer).strip()
    return text + ('\n\n' + warning if warning else '')


def timestamp(record: dict, *, updated: bool = True) -> float:
    keys = ('updated_at', 'updated', 'timestamp', 'created_at', 'created') if updated else ('timestamp', 'created_at', 'created')
    for key in keys:
        value = record.get(key)
        try:
            number = float(value)
            if math.isfinite(number):
                return number
        except (TypeError, ValueError, OverflowError):
            try:
                return datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
            except (ValueError, OverflowError, OSError):
                pass
    return 0.0


def date_label(record: dict) -> str:
    value = timestamp(record)
    if not value:
        return 'Not recorded'
    try:
        return datetime.fromtimestamp(value).astimezone().strftime('%Y-%m-%d %H:%M')
    except (ValueError, OverflowError, OSError):
        return 'Not recorded'


def select(records: list[dict], query: str = '', selected_category: str | None = None,
           sort: str = 'newest') -> list[int]:
    """Viewer-only substring filtering. Stored retrieval/scoring is unchanged."""
    terms = query.casefold().split()
    matches = []
    for index, record in enumerate(records):
        if selected_category is not None and category(record) != selected_category:
            continue
        if terms:
            haystack = (full_text(record) + '\n' + json.dumps(record, ensure_ascii=False)).casefold()
            if not all(term in haystack for term in terms):
                continue
        matches.append(index)
    if sort == 'category':
        matches.sort(key=lambda index: (category(records[index]).casefold(), -timestamp(records[index])))
    else:
        matches.sort(key=lambda index: timestamp(records[index]), reverse=sort != 'oldest')
    return matches


def export_selected(records: list[dict], destination: str) -> None:
    """Explicit user-chosen export only; never change the archive or its metadata."""
    from PyQt6.QtCore import QIODevice, QSaveFile
    from cursiv_engine.core import strand_store, state_store
    target = Path(destination).absolute()
    state_store.checked(target)
    if target.resolve().is_relative_to(strand_store.CURSIV_DIR.resolve()) or any(part.casefold() == '.cursiv' for part in target.parts):
        raise ValueError('Choose an export location outside Cursiv internal data')
    data = json.dumps({'format': 'cursiv-saved-notes-export-v1', 'notes': records},
                      ensure_ascii=True, indent=2, allow_nan=False).encode('utf-8')
    output = QSaveFile(str(target))
    output.setDirectWriteFallback(False)
    if not output.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError(output.errorString())
    if output.write(data) != len(data):
        output.cancelWriting()
        raise OSError(output.errorString())
    if not output.commit():
        raise OSError(output.errorString())
    if target.read_bytes() != data:
        raise OSError('Export verification failed')
