"""Bounded, event-driven investigations. No network, tool execution or model loop."""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from . import curiosity as journal, field_recall, state_store

_busy = threading.Lock()
_metrics = dict(evaluations=0, seconds=0.0, inference_calls=0, failures=0, dropped=0)


def context(person: str, text: str = '') -> tuple[list[dict], list[dict]]:
    """Only authorized field records and this person's explicit memory evidence."""
    from cursiv_v215.memory import semantic, formation
    result = field_recall.query(limit=50)
    if result['warnings']:
        raise ValueError('Field-log integrity warnings require review before curiosity evaluation')
    rows = [r for r in result['records'] if formation.permitted(json.dumps(r, ensure_ascii=False))]
    evidence = [journal.reference('field', r['id'], json.dumps(r, ensure_ascii=False, sort_keys=True),
                                 'Observed fact') for r in rows]
    if semantic.learning_enabled():
        for fact in semantic.list_facts(person)[-30:]:
            if formation.permitted(fact['text']):
                evidence.append(journal.reference('memory', fact['id'], fact['text'],
                    'Reported claim' if fact.get('source') == 'manual' or fact.get('evidence') == 'direct_statement' else 'Inference'))
    if text and formation.permitted(text):
        evidence.append(journal.reference('reported', hashlib.sha256(text.encode()).hexdigest()[:16],
                                         text, 'Reported claim'))
    return rows, evidence


def candidates(rows: list[dict], evidence: list[dict], text: str) -> list[dict]:
    """Conservative transparent rules; differences are not automatically contradictions."""
    out = []
    replaced = {r['corrects'] for r in rows if r.get('corrects')}
    rows = [r for r in rows if r['id'] not in replaced]
    groups = {}
    for row in rows:
        for m in row.get('measurements', []):
            key = (row.get('site', ''), m['name'].lower(), m.get('unit', ''))
            groups.setdefault(key, []).append((row, m))
    for (site, name, unit), items in groups.items():
        unique = {r['id']: (r, m) for r, m in items}
        items = list(unique.values())
        if len(items) < 2 or len({m.get('value') for _, m in items}) < 2:
            continue
        selected = items[:5]
        refs = [dict(source='field', id=r['id']) for r, _ in selected]
        # Scope the claim to available records; these fields may exist elsewhere.
        combined = ' '.join(str(r.get('note', '')) + ' ' + ' '.join(x['name'] for x in r.get('measurements', []))
                            for r, _ in selected).lower()
        if re.search(r'water|ph\b|turbidity|conductivity|soil moisture', name) and not re.search(r'rain|weather|temperature', combined):
            out.append(dict(question=f'Would recording collection conditions help compare {name} at {site or "this site"}?',
                why='Selected records contain different values but do not document rainfall, weather or temperature. '
                    'Their relevance is unestablished; this is not a causal finding.', refs=refs,
                missing_variables=['Collection conditions in selected records'], hypotheses=[],
                investigation='Review the original records and measurement protocol; record relevant conditions in a new observation.'))
        if len(items) >= 3:
            out.append(dict(question=f'What explains the variation in recorded {name} at {site or "this site"}?',
                why='At least three selected observations contain differing values in the same stated unit. '
                    'Timing and methods may explain the difference; no causal relationship is established.',
                refs=refs, hypotheses=['Different conditions or measurement methods (unverified)'],
                investigation='Compare timestamps, sample identities, methods and calibration before drawing conclusions.'))
        # Only flag internally conflicting simultaneous records, not later corrections.
        by_sample = {}
        for row, m in items:
            if row.get('sample_id') and not row.get('corrects'):
                key = (row['sample_id'], row['recorded_utc'])
                by_sample.setdefault(key, []).append((row, m))
        for (sample, timestamp), matching in by_sample.items():
            if len({m.get('value') for _, m in matching}) > 1:
                out.append(dict(question=f'How should differing {name} records for sample {sample} at {timestamp} be reconciled?',
                    why='The same sample, timestamp, measurement name and stated unit have different values. '
                        'Methods and replicate identities remain unknown, so this is a potential record conflict.',
                    refs=[dict(source='field', id=r['id']) for r, _ in matching[:5]],
                    investigation='Check methods and replicate labels. Add a linked correction only if the original is confirmed wrong.'))
    report = next((e for e in evidence if e['source'] == 'reported'), None)
    if report and re.search(r'(?i)\b(?:assume|assuming|must mean|proves that)\b', text):
        out.append(dict(question='What evidence supports this stated assumption: ' + text[:210].strip() + '?',
            why='The user described an assumption or strong conclusion. Its truth has not been established by this evaluation.',
            refs=[dict(source='reported', id=report['id'])],
            investigation='State the assumption explicitly, then identify a comparison or observation that could disconfirm it.'))
    return out[:10]


def evaluate(person: str, project: str = 'general', text: str = '', *, guard=None) -> dict:
    started = time.monotonic()
    rows, evidence = context(person, text)
    proposed = candidates(rows, evidence, text)
    added = []
    for candidate in proposed:
        with state_store.LOCK:
            if guard and not guard():
                break
            record = journal.add(person, project, candidate, evidence)
        if record:
            added.append(record)
    # New references prompt review, not an invented finding of resolution.
    with state_store.LOCK:
        data = journal.load(person)
        changed = False
        for record in data['records'] if not guard or guard() else []:
            if record['project'] != project or record['status'] not in journal.ACTIVE:
                continue
            terms = set(journal.normalize(record['question']).split()) - {'what', 'this', 'that', 'recorded', 'the', 'at', 'in', 'for'}
            prior = {(e['source'], e['id'], e['digest']) for e in record['evidence']}
            linked = [e for e in evidence if (e['source'], e['id'], e['digest']) not in prior and
                      len(terms & set(journal.normalize(e['quote']).split())) >= 2][:5]
            if linked:
                record['evidence'].extend(linked)
                record['reviewed'] = journal.now()
                record['history'].append(dict(at=journal.now(), status=record['status'],
                    note='Related new evidence retrieved; question remains unresolved.',
                    refs=[dict(source=e['source'], id=e['id']) for e in linked]))
                changed = True
        if changed:
            state_store.save(journal.path(person), data)
    elapsed = time.monotonic() - started
    _metrics['evaluations'] += 1
    _metrics['seconds'] += elapsed
    return dict(added=added, candidates=len(proposed), seconds=elapsed, inference_calls=0)


def notify(person: str, project: str = 'general', text: str = '') -> bool:
    """One deferred job at most. Memory queue and conversation remain independent."""
    from cursiv_v215.memory import formation, semantic
    try:
        if not journal.path(person).exists():
            return False  # disabled default does not create journal files
        cfg = journal.load(person)['settings']
        if not cfg['automatic'] or not formation.enabled_for(text or 'field observation updated'):
            return False
        with state_store.LOCK:
            data = journal.load(person)
            data['events'] += 1
            state_store.save(journal.path(person), data)
            eligible = data['events'] % cfg['frequency'] == 0
        if not eligible or not _busy.acquire(blocking=False):
            return False
        epoch = semantic.generation()
        control_epoch = data.get('control_epoch', 0)
        def work():
            try:
                def permitted():
                    current = journal.load(person)
                    return (semantic.generation() == epoch and formation.enabled_for(text or 'field observation updated')
                            and current['settings']['automatic'] and current.get('control_epoch', 0) == control_epoch)
                if permitted():
                    evaluate(person, project, text, guard=permitted)
            except Exception:
                _metrics['failures'] += 1
            finally:
                _busy.release()
        threading.Thread(target=work, daemon=True, name='Cursiv curiosity').start()
        return True
    except (OSError, ValueError):
        _metrics['failures'] += 1
        return False


def suggestion(person: str, project: str = 'general') -> str:
    with state_store.LOCK:
        data = journal.load(person)
        if not data['settings']['suggestions'] or not data['settings']['automatic']:
            return ''
        from cursiv_v215.memory import semantic
        if not semantic.learning_enabled():
            return ''
        # At most one suggestion in 24 hours, and never the same investigation twice.
        recent = [r['surfaced'] for r in data['records'] if r.get('surfaced')]
        if recent:
            from datetime import datetime, timezone
            if (datetime.now(timezone.utc) - datetime.fromisoformat(max(recent))).total_seconds() < 86400:
                return ''
        eligible = [r for r in data['records'] if r['project'] == project and r['status'] in journal.ACTIVE and not r['surfaced']]
        if not eligible:
            return ''
        record = max(eligible, key=lambda r: r['score'])
        record['surfaced'] = journal.now()
        state_store.save(journal.path(person), data)
        return f"Question to investigate [{record['id']}]: {record['question']} Type curiosity show {record['id']} for its evidence."


def command(text: str, person: str, project: str = 'general') -> str | None:
    low = text.strip().lower().rstrip('.?')
    evaluate_requests = ('what are we missing?', "what haven't we considered?", "what’s unusual about these observations?",
        "what's unusual about these observations?", 'what questions should we be asking?',
        'revisit our unresolved questions.', 'revisit our unresolved questions', 'challenge my assumptions.',
        'challenge my assumptions', 'what alternative explanations should we investigate?',
        "what are you still trying to figure out about this project?", "did today's observations resolve any earlier questions?")
    evaluate_requests = tuple(value.rstrip('.?') for value in evaluate_requests)
    if not (low.startswith('curiosity') or low in evaluate_requests or low == 'show me your curiosity journal'
            or low == 'what evidence would help answer this'):
        return None
    try:
        if low == 'what evidence would help answer this':
            active = [r for r in journal.load(person)['records'] if r['project'] == project and r['status'] in journal.ACTIVE]
            return journal.render(active) if len(active) == 1 else 'Choose an investigation with curiosity show <CUR-id> to review its evidence and next action.'
        if low in evaluate_requests or low == 'curiosity evaluate':
            report = evaluate(person, project, text if low.startswith('challenge') else '')
            return (f"Evaluation completed: {report['candidates']} candidate(s), {len(report['added'])} new entry/entries; "
                    'no automatic resolution or causal conclusion.\n' + journal.render([
                        r for r in journal.load(person)['records'] if r['project'] == project and r['status'] in journal.ACTIVE]))
        if low == 'curiosity settings':
            return json.dumps(journal.load(person)['settings'])
        setting = re.fullmatch(r'curiosity (automatic|suggestions) (on|off)', low)
        numeric = re.fullmatch(r'curiosity (frequency|max_active) (\d+)', low)
        if setting or numeric:
            m = setting or numeric
            journal.configure(person, **{m[1]: m[2] == 'on' if setting else int(m[2])})
            return 'Curiosity setting saved and verified.'
        if low.startswith('curiosity add '):
            record = journal.add(person, project, dict(question=text.strip()[14:]), [], manual=True)
            return journal.render([record]) if record else 'Duplicate question or active budget reached; no entry added.'
        m = re.fullmatch(r'curiosity (dismiss|open|reopen|investigate|await|supersede|resolve) (CUR-[a-f0-9]+)(?: :: (.+))?', text.strip(), re.I)
        if m:
            status = dict(dismiss='Dismissed', open='Open', reopen='Open', investigate='Investigating',
                          await_='Awaiting evidence', supersede='Superseded', resolve='Resolved').get(m[1].lower(), 'Awaiting evidence')
            resolution = []
            if m[1].lower() == 'resolve' and m[3]:
                ident = m[3].strip()
                source, _, target = ident.partition(':')
                if source == 'field':
                    found = field_recall.query(entry=target)
                    if found['warnings']:
                        raise ValueError('Field integrity warnings require review before resolution')
                    resolution = [journal.reference('field', r['id'], json.dumps(r, ensure_ascii=False, sort_keys=True),
                                  'Observed fact') for r in found['records'] if r['id'] == target]
                elif source == 'memory':
                    from cursiv_v215.memory import semantic
                    resolution = [journal.reference('memory', f['id'], f['text'], 'Reported claim')
                                  for f in semantic.list_facts(person) if f['id'] == target and
                                  (f.get('source') == 'manual' or f.get('evidence') == 'direct_statement')]
                from cursiv_v215.memory import formation
                resolution = [e for e in resolution if formation.permitted(e['quote'])]
                if not resolution:
                    raise ValueError('Resolution must reference a currently readable field:<id> or memory:<id>')
            journal.transition(person, m[2], status, resolution)
            return 'Investigation state saved and verified.'
        if low.startswith('curiosity review '):
            ident = text.strip()[17:].strip()
            ident = 'CUR-' + ident[4:].lower() if ident.lower().startswith('cur-') else ident
            record = next((r for r in journal.load(person)['records'] if r['id'] == ident), None)
            if record is None:
                raise ValueError('No such curiosity entry')
            _, current = context(person)
            available = {(e['source'], e['id'], e['digest']) for e in current}
            return '\n'.join(f"[{e['source']}:{e['id']}] " +
                ('Still readable in the bounded retrieval' if (e['source'], e['id'], e['digest']) in available else
                 'Not present in current bounded retrieval; original source may be missing, changed or outside the selection')
                for e in record['evidence']) or 'No supporting evidence; this is a manually proposed question.'
        if low.startswith('curiosity show '):
            ident = text.strip()[15:].strip()
            ident = 'CUR-' + ident[4:].lower() if ident.lower().startswith('cur-') else ident
            return journal.render([r for r in journal.load(person)['records'] if r['id'] == ident])
        if low == 'curiosity export':
            output = journal.path(person).with_suffix('.export.json')
            state_store.save(output, journal.load(person))
            return f'Journal export saved and verified: {output}'
        if low == 'curiosity clear confirm':
            with state_store.LOCK:
                data = journal.load(person)
                data.update(records=[], events=0)
                data['control_epoch'] = data.get('control_epoch', 0) + 1
                data['settings'].update(automatic=False, suggestions=False)
                state_store.save(journal.path(person), data)
            return 'Journal cleared; automatic curiosity disabled. Previous data remains in verified local backups.'
        if low in ('curiosity', 'curiosity journal', 'show me your curiosity journal'):
            return journal.render(sorted(journal.load(person)['records'], key=lambda r: -r['score']))
        return ('Curiosity commands: journal; evaluate; add <question>; show <CUR-id>; '
                'open|investigate|await|dismiss|reopen|supersede <CUR-id>; resolve <CUR-id> :: field:<entry-id>; '
                'automatic on|off; suggestions on|off; frequency <1–100>; max_active <1–20>; settings; export; clear confirm. '
                'Clearing retains recovery backups; erase those separately if permanent deletion is intended.')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return f'Curiosity operation failed: {type(exc).__name__}: {exc}. No persistence success is claimed.'
