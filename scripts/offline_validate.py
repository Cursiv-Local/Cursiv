"""Run applicable tests with no DNS, socket traffic, inference services or unsafe children.
Usage: locked-python scripts/offline_validate.py LABEL [pytest arguments]
"""
from pathlib import Path
import hashlib,json,os,re,shutil,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
label=sys.argv[1] if len(sys.argv)>1 else ''
if not re.fullmatch(r'[a-z0-9-]{1,60}',label):raise SystemExit('Use a new lowercase receipt label')
receipt=ROOT/'bench/results'/('U113-offline-'+label+'.json')
if receipt.exists():raise SystemExit('Refusing to overwrite existing offline receipt')
home=Path(tempfile.mkdtemp(prefix='cursiv-strict-offline-'));guarddir=home/'guard';guarddir.mkdir();logs=home/'guard-logs';logs.mkdir()
shutil.copyfile(ROOT/'scripts/offline_guard.py',guarddir/'offline_guard.py')
(guarddir/'sitecustomize.py').write_text('import offline_guard; offline_guard.install()\n',encoding='utf-8')
for key in ('HOME','USERPROFILE','CURSIV_REAL_HOME'):os.environ[key]=str(home)
for key,folder in [('CURSIV_APP_DATA','app'),('APPDATA','roaming'),('LOCALAPPDATA','local')]:os.environ[key]=str(home/folder)
for key in list(os.environ):
    if re.search(r'(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET_KEY|CURSIV_LIVE)',key,re.I):os.environ.pop(key,None)
os.environ.update(CURSIV_STRICT_HOME=str(home),CURSIV_STRICT_GUARD=str(guarddir),CURSIV_STRICT_LOG=str(logs),
 CURSIV_STRICT_EXCLUSIONS=str(home/'exclusions.json'),PYTHONPATH=os.pathsep.join([str(guarddir),str(ROOT),str(ROOT/'launcher'),str(ROOT/'tests')]),
 PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',QT_QPA_PLATFORM='offscreen',CURSIV_NO_ENGINE_START='1',CURSIV_PORTABLE='0',CURSIV_USB_ROOT='',CURSIV_LIVE='0',
 GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=str(home/'empty-gitconfig'),GIT_PAGER='cat')
(home/'empty-gitconfig').write_text('');(home/'empty-hooks').mkdir()
os.environ.update(GIT_CONFIG_COUNT='2',GIT_CONFIG_KEY_0='core.hooksPath',GIT_CONFIG_VALUE_0=str(home/'empty-hooks'),GIT_CONFIG_KEY_1='core.fsmonitor',GIT_CONFIG_VALUE_1='false')
(home/'tmp').mkdir()
os.environ.update(TEMP=str(home/'tmp'),TMP=str(home/'tmp'))
tempfile.tempdir=str(home/'tmp')
sys.path[:0]=[str(guarddir),str(ROOT),str(ROOT/'launcher'),str(ROOT/'tests')];os.chdir(ROOT)
import offline_guard
offline_guard.install()
refresh='--refresh-index' in sys.argv
if refresh:
    sys.argv.remove('--refresh-index')
    from cursiv_engine.core import self_index,self_source
    (ROOT/'cursiv_engine/core/own_source_index.json').write_text(json.dumps(self_index.build(ROOT,self_source.version()),separators=(',',':'))+'\n',encoding='utf-8')
import pytest
args=sys.argv[2:] or ['tests','-q','--tb=short']
xml=ROOT/'bench/results'/('U113-offline-'+label+'.xml')
code=pytest.main([*args,'-p','offline_validation_plugin','--basetemp',str(home/'pytest'),'--junitxml',str(xml)])
events=[]
for file in logs.glob('*.jsonl'):
    events.extend(json.loads(row) for row in file.read_text(encoding='utf-8').splitlines())
blocked=[e for e in events if e['event']=='blocked']
result=dict(label=label,exit_code=int(code or bool(blocked)),pytest_exit_code=int(code),scope='Python audit guard before pytest/application import; propagated startup guard for approved Python children; no OS-wide firewall claim',
 guard_sha256=hashlib.sha256((ROOT/'scripts/offline_guard.py').read_bytes()).hexdigest(),events=events,blocked_operations=blocked,
 exclusions=json.loads((home/'exclusions.json').read_text()) if (home/'exclusions.json').exists() else [],junit=str(xml.relative_to(ROOT)))
receipt.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('Strict offline receipt:',receipt.name,'blocked unexpected operations:',len(blocked),flush=True)
raise SystemExit(code or bool(blocked))
