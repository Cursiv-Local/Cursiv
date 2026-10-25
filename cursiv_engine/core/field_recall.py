"""Application-controlled historical field retrieval. Never writes field records."""
from __future__ import annotations

from datetime import date, timedelta
import json
import re
from . import fieldlog, state_store

MAX_BYTES = 64 * 1024 * 1024
MAX_ROWS = 100000


def query(*, words: str = '', sample: str = '', start: str = '', end: str = '',
          entry: str = '', corrections: bool = False, limit: int = 10, offset: int = 0) -> dict:
    """Read one authorized notebook, verifying chain while scanning bounded input."""
    path = state_store.checked(fieldlog.log_file())
    if not path.parent.exists():
        from .paths import portable_root
        root = portable_root()
        if root and not root.exists():
            raise OSError('Portable drive unavailable')
    limit, offset = max(1, min(int(limit), 50)), max(0, int(offset))
    for value in (start, end):
        if value:
            date.fromisoformat(value)
    if start and end and start > end:
        raise ValueError('Start date is after end date')
    rows, warnings, size, previous, sequence = [], [], 0, fieldlog.GENESIS, 0
    import io
    from . import private_store
    try:
        if path.stat().st_size > MAX_BYTES * 2:
            raise ValueError('Field log exceeds safe scan budget; use an authorized smaller export for review')
        stream = io.BytesIO(private_store.read_bytes(path))       # encrypted on a computer (U98)
    except FileNotFoundError:
        return dict(records=[], total=0, offset=offset, more=False, warnings=[], source='field log')
    with stream:
        for n in range(1, MAX_ROWS + 2):
            line = stream.readline(1024 * 1024 + 1)
            if not line:
                break
            size += len(line)
            if n > MAX_ROWS or size > MAX_BYTES or len(line) > 1024 * 1024:
                raise ValueError('Field log exceeds safe scan budget; use an authorized smaller export for review')
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict) or fieldlog.record_problems(row) or row.get('schema', 0) > fieldlog.SCHEMA:
                    raise ValueError('invalid record')
            except (ValueError, TypeError, UnicodeError):
                warnings.append(f'Line {n} is damaged or unsupported; not used as evidence')
                continue
            if (row.get('prev') != previous or row.get('seq') != sequence + 1
                    or fieldlog._fingerprint(row) != row.get('hash')):
                warnings.append(f'Integrity check failed at entry {row.get("id", n)}; not used as evidence')
                previous, sequence = row.get('hash'), row.get('seq', sequence)
                continue
            previous, sequence = row['hash'], row['seq']
            rows.append(row)
    # Filtering never rewrites or repairs the authoritative chain.
    if entry:
        ids = {entry}
        ids.update(r['id'] for r in rows if str(r['seq']) == entry.lstrip('#'))
        for _ in range(len(rows) + 1):
            related = {r['id'] for r in rows if r.get('corrects') in ids}
            related |= {r['corrects'] for r in rows if r['id'] in ids and r.get('corrects')}
            if related <= ids:
                break
            ids |= related
        rows = [r for r in rows if r['id'] in ids or str(r['seq']) == entry.lstrip('#')]
    mentions = []
    if sample:
        everything = rows
        rows = [r for r in rows if r.get('sample_id', '').casefold() == sample.casefold()]
        if not rows:
            # No record has that sample ID; say which ones only mention it (U100 audit: W-003 was in a note).
            mentions = [r for r in everything if sample.casefold() in ' '.join(
                str(r.get(k, '')) for k in ('site', 'project', 'note', 'measurements')).casefold()][-10:]
    if start:
        rows = [r for r in rows if r['recorded_local'][:10] >= start]
    if end:
        rows = [r for r in rows if r['recorded_local'][:10] <= end]
    if words:
        terms = re.findall(r'[\w.-]+', words.casefold())
        rows = [r for r in rows if all(term in ' '.join(str(r.get(k, '')) for k in
                ('site', 'sample_id', 'project', 'note', 'measurements', 'reason')).casefold() for term in terms)]
    if corrections:
        rows = [r for r in rows if r.get('corrects')]
    total = len(rows)
    selected = list(reversed(rows))[offset:offset + limit]
    return dict(records=selected, total=total, offset=offset, more=offset + limit < total,
                warnings=warnings[:20], source='field log', mentions=list(reversed(mentions)), sample=sample)


def is_request(text: str) -> bool:
    if text.strip().lower() in ('field log', 'fieldlog', 'field notes', 'show field log'):
        return True
    return bool(re.search(r'(?i)^(?:field\s*log (?:search|entry|sample|recent|since|between|corrections)\b)|'
        r'\b(?:what did I (?:record|log)|(?:find|show|summari[sz]e|search|retrieve|recall|what|which)\b.*'
        r'\b(?:observations?|field (?:log|notes|session)|research notes|measurements.*sample)|'
        r'what corrections have I made)', text))


def request(text: str) -> dict | None:
    if not is_request(text):
        return None
    low = text.lower()
    if 'last field session' in low:
        return {'clarification': 'Field records have no session identifier. Choose a date range or sample ID.'}
    filters = {}
    today = date.today()
    if 'yesterday' in low:
        filters.update(start=str(today - timedelta(days=1)), end=str(today - timedelta(days=1)))
    elif 'last week' in low:
        monday = today - timedelta(days=today.weekday())
        filters.update(start=str(monday - timedelta(days=7)), end=str(monday - timedelta(days=1)))
    elif 'today' in low:
        filters.update(start=str(today), end=str(today))
    dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', text)
    if dates:
        filters.update(start=dates[0], end=dates[-1] if len(dates) > 1 or 'since' not in low else '')
    sample = re.search(r'(?i)\bsample\s+([\w.-]+)', text)
    if sample:
        filters['sample'] = sample[1].rstrip('.?')
    entry = re.search(r'(?i)^field\s*log entry\s+([\w#-]+)', text)
    if entry:
        filters['entry'] = entry[1]
    count = re.search(r'(?i)\b(?:last|latest|recent)\s+(ten|\d+)\b', text)
    if count:
        filters['limit'] = 10 if count[1].lower() == 'ten' else int(count[1])
    page = re.search(r'(?i)\boffset\s+(\d+)\b', text)
    if page:
        filters['offset'] = int(page[1])
    if 'correction' in low and not entry:
        filters['corrections'] = True
    terms = re.search(r'(?i)(?:mentioning|about|search)\s+(.+?)[?.!]*$', text)
    if terms and not sample:
        filters['words'] = terms[1].strip(' .?!"\'')
    return query(**filters)


def render(result: dict, *, summarize: bool = False) -> str:
    if 'clarification' in result:
        return result['clarification']
    lines = ['Field-log retrieval: ' + str(result['total']) + ' matching record(s).']
    lines += ['Warning: ' + w for w in result['warnings']]
    if not result['records']:
        lines.append('No matching entries were found in the readable, integrity-checked records.')
        if result.get('mentions'):
            lines.append(f"No record has sample ID {result['sample']}, but {len(result['mentions'])} mention it in their text:")
            lines += ['[' + row['id'] + '] ' + fieldlog.summary(row) for row in result['mentions']]
    if summarize and result['records']:
        lines.append('Extractive summary of recorded observations; no causal interpretation was generated.')
    for row in result['records']:
        lines.append('[' + row['id'] + '] ' + fieldlog.summary(row))
    if result['more']:
        lines.append(f"More records available. Repeat with offset {result['offset'] + len(result['records'])}.")
    return '\n'.join(lines)


# "What was the average water temperature in my TEST-U96 samples?" The model got
# this right once but labelled it as coming from an imported document; the
# notebook can answer it exactly, with the records it used.
_STAT = re.compile(r"(?i)^(?:what(?:'s| is| was| were)\s+)?(?:the\s+)?"
                   r"(average|mean|median|minimum|maximum|min|max|highest|lowest|range)\s+(?:of\s+)?(?:the\s+|my\s+)?"
                   r"(.+?)\s+(?:in|of|across|for|from|at)\s+(?:all\s+)?(?:my\s+|the\s+)?(.*?)\s*"
                   r"(?:samples?|records?|entries|observations|readings|field\s*log|notebook)\b[^?]*[?.!]?$")


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r'[a-z0-9]+', text.casefold().replace('temperature', 'temp'))]


def stats_command(text: str) -> str | None:
    m = _STAT.match(text.strip())
    if not m:
        return None
    kind, measure, scope = m[1].lower(), _words(m[2]), m[3].strip().casefold()
    if not measure:
        return None
    rows, offset = [], 0
    while True:
        page = query(limit=50, offset=offset)
        rows += page['records']
        if not page['more']:
            break
        offset += 50
    superseded = {r['corrects'] for r in rows if r.get('corrects')}
    used = []
    for r in rows:
        if r['id'] in superseded:
            continue
        if scope and scope not in ('my', 'all') and scope not in (r.get('sample_id', '') + ' ' + r.get('site', '')).casefold():
            continue
        for item in r.get('measurements') or []:
            if isinstance(item.get('number'), (int, float)) and all(w in _words(item.get('name', '')) for w in measure):
                used.append((r, item))
                break
    label = m[2].strip()
    where = f' in {m[3].strip()} records' if scope else ''
    if not used:
        return (f'No recorded {label} values{where} were found in the field notebook, so nothing was calculated.'
                '\n\n*[Sources: your field notebook (no AI model)]*')
    units = {str(item.get('unit') or '').strip() for _, item in used}
    if len(units) > 1:
        return (f'The {label} records{where} use different units ({", ".join(sorted(units))}), so Cursiv did not combine them.'
                '\n\n*[Sources: your field notebook (no AI model)]*')
    unit = (' ' + units.pop()) if units and next(iter(units), '') else ''
    values = [float(item['number']) for _, item in used]
    import statistics
    result = {'average': statistics.fmean(values), 'mean': statistics.fmean(values), 'median': statistics.median(values),
              'minimum': min(values), 'min': min(values), 'lowest': min(values),
              'maximum': max(values), 'max': max(values), 'highest': max(values),
              'range': max(values) - min(values)}[kind]
    name = {'mean': 'average', 'min': 'minimum', 'lowest': 'minimum', 'max': 'maximum', 'highest': 'maximum'}.get(kind, kind)
    shown = f'{result:.2f}'.rstrip('0').rstrip('.')
    lines = [f'The {name} {label}{where} is {shown}{unit}, from {len(values)} record(s):']
    lines += [f'- [{r["id"]}] {r.get("sample_id") or r.get("site") or "#" + str(r["seq"])}: {item["number"]:g}{unit}'
              for r, item in used]
    return '\n'.join(lines) + '\n\n*[Sources: your field notebook, calculated by Cursiv (no AI model)]*'


def command(text: str) -> str | None:
    try:
        stat = stats_command(text)
        if stat is not None:
            return stat
        result = request(text)
        return render(result, summarize=bool(re.search(r'(?i)summari[sz]', text))) if result is not None else None
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return f'Field-log retrieval failed: {type(exc).__name__}: {exc}. No historical answer was generated.'
