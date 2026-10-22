"""Short, factual presentation of application results; never parse model prose."""
from pathlib import Path

VOICE = (
    'Use a calm, precise, slightly warm voice. Answer directly in plain words. '
    'Avoid decorative emoji, stock reassurance and routine closing offers or questions. '
    'Ask one question only when it helps resolve something important. '
    'Acknowledge a conversation preference briefly; never imply a persistent save without '
    'a confirmed application receipt. Follow the person\'s requested tone and format.'
)


def file_receipt(row: dict) -> str:
    if not row.get('ok') or not row.get('verified'):
        return 'File action not confirmed · ' + str(row.get('error') or 'no verified result')
    name = Path(row.get('path') or '').name or 'workspace'
    operation = row.get('operation')
    if operation == 'list_directory':
        n = len(row.get('entries') or [])
        return f'Listed {n} item' + ('' if n == 1 else 's') + f' · {name}'
    if operation == 'search_files':
        n = len(row.get('entries') or [])
        return f'Found {n} matching item' + ('' if n == 1 else 's')
    if operation == 'read_file':
        return f'Read {name}' + (' · partial result' if row.get('truncated') else '')
    if operation == 'create_directory':
        return f'Created directory · {name}'
    if operation in ('write_file', 'append_file', 'create_file'):
        return f'Saved {name} · {row.get("byte_count", 0)} bytes · read-back matched'
    return 'File operation completed · see result'


def notebook_receipt(row: dict) -> str:
    status = row.get('status')
    if not row.get('ok'):
        return 'Field Notebook · ' + ('details needed' if status == 'clarification' else 'action not confirmed')
    records = row.get('records') or []
    if status in ('saved', 'already_recorded') and records:
        record = records[0]
        lead = 'Recorded' if status == 'saved' else 'Already recorded · no duplicate added'
        sample = f' · sample {record["sample_id"]}' if record.get('sample_id') else ''
        return f'{lead} · record {record["id"]}{sample} · fingerprint {record["hash"][:12]} · chain intact'
    if status == 'verified':
        return f'{row.get("count", 0)} notebook entries · chain intact'
    return f'{row.get("count", 0)} matching notebook entries'


def memory_receipt(row: dict) -> str:
    if not row.get('ok'):
        return 'Memory action not confirmed'
    actions = row.get('outcomes') or []
    saved = [o for o in actions if o.get('operation') in ('SAVE_MEMORY', 'UPDATE_MEMORY')]
    ids = [str(r['id']) for o in saved for r in o.get('records', []) if r.get('id')]
    if ids:
        return 'Saved memory · ' + ', '.join(ids)
    return 'Memory request completed · see result'


def review_status(result) -> str:
    if result is None or result.status == 'skipped' or (result.clear and result.status != 'revised'):
        return ''
    if result.status == 'unavailable':
        return 'Check unavailable · see note'
    if result.status == 'revised' and result.clear:
        return 'Checked · suggested revision'
    n = len(result.issues) or len(result.problems)
    return f'Checked · {n} note' + ('' if n == 1 else 's') if n else 'Check incomplete · see note'
