"""Real local Qwen regression probes with disposable stores and paired note scoring.

Run with --set worksheet|science|calculation --output <new file>. The existing desktop-command
and completion driver observes actual localhost transport, fixes seed/temperature,
and refuses online calls/model switches. Native replies are recorded as zero model
requests. Confirmation UI is covered separately by the Qt regression sequence.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TASK_HOME = Path(tempfile.mkdtemp(prefix='cursiv_u109_post_live_'))
os.environ.update(HOME=str(TASK_HOME), USERPROFILE=str(TASK_HOME), CURSIV_REAL_HOME=str(TASK_HOME),
    CURSIV_APP_DATA=str(TASK_HOME/'app'), APPDATA=str(TASK_HOME/'roaming'), LOCALAPPDATA=str(TASK_HOME/'local'),
    CURSIV_NO_ENGINE_START='1', QT_QPA_PLATFORM='offscreen', CURSIV_PORTABLE='0', CURSIV_USB_ROOT='')
sys.path[:0] = [str(ROOT), str(ROOT/'launcher'), str(ROOT/'scripts')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--set', choices=('worksheet', 'science', 'calculation'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Never overwrite evidence'
    corpus_path = ROOT/'bench/u109-postrelease-live.json'
    corpus = json.loads(corpus_path.read_text(encoding='utf-8'))
    import u108_live_bench as live
    from cursiv_engine.ui import chat_app as ca
    from cursiv_engine.memory import semantic, intents
    if args.set == 'worksheet':
        semantic.set_person('worksheet')
        assert intents.command('remember I prefer casual replies, like two researchers having coffee',
                               [], person='worksheet').ok
    captures = []
    original_call = ca._call_ollama
    def capture(*values, **kwargs):
        record = dict(messages=values[0] if values else kwargs.get('messages', []), text='')
        captures.append(record)
        for chunk in original_call(*values, **kwargs):
            record['text'] += str(chunk)
            yield chunk
    ca._call_ollama = capture
    live.CASES = corpus[args.set]
    live.HISTORIES = {key: [] for key, _ in live.CASES}
    original_mkdtemp = tempfile.mkdtemp
    live.tempfile.mkdtemp = lambda *a, **kw: original_mkdtemp(prefix='cursiv_u109_post_driver_')
    sys.argv = [sys.argv[0], '--output', str(args.output)]
    live.main()
    result = json.loads(args.output.read_text(encoding='utf-8'))
    result.update(set=args.set, corpus_sha256=hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        raw_model_generations=captures, baseline_source='immutable U109; paired scoring of identical final drafts')
    if args.set == 'science':
        from cursiv_engine.core import science_check
        source = subprocess.check_output(['git', 'show',
            'bdf2737446f77a81e14a19f774c99c12a4bb3bcf:cursiv_engine/core/science_check.py'], cwd=ROOT)
        baseline_path = TASK_HOME/'science_check_u109.py'
        baseline_path.write_bytes(source)
        spec = importlib.util.spec_from_file_location('science_check_u109_baseline', baseline_path)
        baseline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(baseline)
        for row in result['rows']:
            draft = row['response'].split('\n\n' + science_check.OVERCONFIDENCE_MARK)[0]
            authored = 'model' if row['calls'] else 'native'
            row.update(authored=authored, draft=draft,
                before_note=baseline.overconfidence_note(row['question'], draft),
                after_note=science_check.overconfidence_note(row['question'], draft, authored=authored))
        result['paired_note_counts'] = {kind: {phase: sum(bool(r[phase+'_note']) for r in result['rows']
            if r['id'].startswith(kind+'-')) for phase in ('before', 'after')} for kind in ('control', 'risk')}
        result['baseline_rule_sha256'] = hashlib.sha256(source).hexdigest()
    changed = subprocess.check_output(['git','diff','--name-only','--','*.py'],cwd=ROOT,text=True).splitlines()
    result['working_source_sha256'] = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in changed}
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
