"""Real Qwen self-inspection probes; own-source access is restricted to public code."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
home = Path(tempfile.mkdtemp(prefix='u108-self-live-', dir=ROOT/'reports'))
os.environ.update(HOME=str(home), USERPROFILE=str(home), CURSIV_APP_DATA=str(home/'app'), CURSIV_NO_ENGINE_START='1')
sys.path[:0] = [str(ROOT), str(ROOT/'launcher')]
from cursiv_engine.core import self_source
paths = subprocess.check_output(['git','ls-files','cursiv_engine/*.py','launcher/*.py',
                                 'docs/CODE-MAP.md','ARCHITECTURE.md'], cwd=ROOT, text=True).splitlines()
public = [p for p in paths if not p.startswith('cursiv_engine/station/')]
self_source.files = lambda: public
selected = 'development'
if '--set' in sys.argv:
    at = sys.argv.index('--set')
    selected = sys.argv[at+1]
    del sys.argv[at:at+2]
if selected not in ('development','heldout','controlflow','contracts','banter'):
    raise SystemExit('Unknown frozen set')
corpus_path = ROOT/({'controlflow':'bench/u108-self-control-flow.json','contracts':'bench/u108-self-contracts.json','banter':'bench/u108-banter.json'}.get(selected,'bench/u108-self-inspection.json'))
corpus = json.loads(corpus_path.read_text(encoding='utf-8'))['heldout' if selected in ('controlflow','contracts','banter') else selected]
import u108_live_bench as harness
harness.CASES = [(case['id'],case['question']) for case in corpus]
harness.HISTORIES = {case['id']:[dict(role='user',content=q) for q in case['history']] for case in corpus}
if __name__ == '__main__':
    harness.main()
