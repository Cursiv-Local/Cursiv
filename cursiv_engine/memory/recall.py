"""Date-scoped saved-fact retrieval. No model, embeddings, migration or writes."""
from datetime import date, datetime, timedelta
import re


def today() -> date:
    return datetime.now().astimezone().date()


def window(period: str) -> tuple[date, date]:
    t = period.lower().strip().rstrip('.!?')
    t = re.sub(r'^(?:the\s+)?(?:past|passed|last)\s+', '', t)
    if t == 'today':
        return today(), today()
    if t == 'yesterday':
        day = today() - timedelta(days=1)
        return day, day
    numbers = dict(one=1, two=2, three=3, four=4, a=1, an=1)
    m = re.fullmatch(r'(\d+|one|two|three|four|a|an)\s+(days?|weeks?)', t)
    if m:
        n = int(m[1]) if m[1].isdigit() else numbers[m[1]]
        days = n * (7 if m[2].startswith('week') else 1)
        if not 1 <= days <= 3660:
            raise ValueError('Choose between 1 and 3660 days')
        return today() - timedelta(days=days - 1), today()
    m = re.fullmatch(r'(?:between\s+)?(\d{4}-\d{2}-\d{2})\s+(?:and|to|through)\s+(\d{4}-\d{2}-\d{2})', t)
    if m:
        start, end = date.fromisoformat(m[1]), date.fromisoformat(m[2])
        if start > end:
            raise ValueError('Start date must be on or before end date')
        return start, end
    raise ValueError('Use past 14 days, past two weeks, today, yesterday, or YYYY-MM-DD to YYYY-MM-DD')


def saved_day(record: dict) -> date | None:
    value = record.get('created') or record.get('date')
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return (parsed.astimezone() if parsed.tzinfo else parsed).date()
    except ValueError:
        return None


def retrieve(period: str, person: str) -> tuple[str, list[dict]]:
    from . import semantic as sem
    start, end = window(period)
    facts, damaged = sem._read_facts()
    visible = [f for f in facts if f.get('person') in (person, sem.SHARED)
               and f.get('status', 'active') == 'active']
    matches, undated = [], 0
    for record in visible:
        day = saved_day(record)
        if day is None:
            undated += 1
        elif start <= day <= end:
            matches.append(record)
    matches.sort(key=lambda f: (saved_day(f), str(f.get('created', '')), str(f.get('id', ''))))
    shown = matches[-40:]
    head = (f'{len(matches)} matching saved memory records · {start.isoformat()} through {end.isoformat()} '
            f'(inclusive local calendar dates); showing {len(shown)}.')
    rows = '\n'.join(f"- [{f.get('id', 'legacy record without ID')}] {f['text']} "
                     f"(saved {f.get('created') or f.get('date')}; {sem.origin_label(f)})" for f in shown)
    scope = ('This searches active saved facts visible to this user, not the complete conversation archive or Field Notebook. '
             'Dates describe when records were saved, not when the described events occurred. '
             'Older timestamps without a timezone are interpreted as local calendar dates.')
    warnings = (f'\n{undated} visible record(s) have no usable saved date; '
                f'{len(damaged)} store line(s) are unreadable. No complete-history claim is possible.'
                if undated or damaged else '\nA missing match does not establish that an event never happened or was never discussed.')
    return head + '\n' + (rows or 'No matching readable saved facts.') + '\n' + scope + warnings, shown
