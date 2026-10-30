"""Fail-closed Python test guard. No application imports or transport calls."""
import atexit
from contextlib import contextmanager
import importlib.abc
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import shutil

_installed=False
current_test=os.environ.get('CURSIV_STRICT_TEST','startup')
violations=[]
_expected=0

@contextmanager
def expected_denial():
    global _expected
    _expected+=1
    try:yield
    finally:_expected-=1
NETWORK={'socket.connect','socket.getaddrinfo','socket.gethostbyname','socket.gethostbyname_ex',
         'socket.gethostbyaddr','socket.sendto','socket.sendmsg','socket.bind'}
class OfflineViolation(RuntimeError):pass

def emit(kind,**values):
    folder=os.environ.get('CURSIV_STRICT_LOG')
    if folder:
        raw=(json.dumps(dict(pid=os.getpid(),event=kind,test=current_test,**values))+'\n').encode()
        fd=os.open(str(Path(folder)/(str(os.getpid())+'.jsonl')),os.O_CREAT|os.O_APPEND|os.O_WRONLY,0o600)
        try:os.write(fd,raw)
        finally:os.close(fd)

def deny(kind):
    if _expected:emit('expected_guard_denial',operation=kind)
    else:
        import traceback
        violations.append((current_test,kind))
        emit('blocked',operation=kind,frames=[dict(file=Path(f.filename).name,function=f.name,line=f.lineno) for f in traceback.extract_stack(limit=20)[:-1]])
    raise OfflineViolation('Strict offline validation blocked '+kind)

class RestrictedImports(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='cursiv_engine.station' or fullname.startswith('cursiv_engine.station.'):
            deny('excluded Field Station import')
        if fullname.startswith(('PyQt6.QtNetwork','PyQt6.QtWebEngine')):
            deny('native networking module import')

def install():
    global _installed
    if _installed:return
    _installed=True
    home=Path(os.environ['CURSIV_STRICT_HOME']).resolve()
    guard=Path(os.environ['CURSIV_STRICT_GUARD']).resolve()
    python=Path(sys.executable).resolve()
    original=subprocess.Popen
    pending=threading.local()
    trusted_git=Path(shutil.which("git") or "git").resolve()
    class GuardedPopen(original):
        def __init__(self,args,*pos,**kw):
            if kw.get('shell'):deny('shell subprocess')
            if isinstance(args,(str,bytes)):deny('unstructured subprocess')
            command=[os.fspath(x) for x in args]
            env=dict(os.environ if kw.get('env') is None else kw['env'])
            for key in ('CURSIV_STRICT_HOME','CURSIV_STRICT_GUARD','CURSIV_STRICT_LOG'):
                env[key]=os.environ[key]
            env.update(CURSIV_NO_ENGINE_START='1',QT_QPA_PLATFORM='offscreen',CURSIV_LIVE='0')
            env['CURSIV_STRICT_TEST']=current_test
            env['PYTHONPATH']=str(guard)+os.pathsep+env.get('PYTHONPATH','')
            env['PYTHONIOENCODING']='utf-8'
            kw['env']=env
            pending.command=command
            try:super().__init__(command,*pos,**kw)
            finally:pending.command=None
    subprocess.Popen=GuardedPopen
    original_run=subprocess.run
    def run(args,*pos,**kw):
        if isinstance(args,(list,tuple)) and list(args)==['nvidia-smi','--query-gpu=memory.total','--format=csv,noheader,nounits']:
            emit('mocked_hardware_query')
            return subprocess.CompletedProcess(args,0,stdout='0\n',stderr='')
        return original_run(args,*pos,**kw)
    subprocess.run=run
    def audit(event,args):
        if event in NETWORK:deny(event)
        if event in ('os.system','os.posix_spawn','os.posix_spawnp','os.startfile','os.exec'):
            deny(event)
        if event!='subprocess.Popen':return
        executable,argv,cwd,env=args
        if isinstance(argv,str):
            saved=getattr(pending,'command',None)
            if saved is None or subprocess.list2cmdline(saved)!=argv:deny('unstructured subprocess command string')
            words=saved
        elif isinstance(argv,(list,tuple)):words=[os.fspath(w) for w in argv]
        else:deny('unstructured subprocess arguments')
        name=Path(words[0]).name.lower()
        resolved=Path(shutil.which(words[0]) or words[0]).resolve()
        if resolved in (python,Path(getattr(sys,'_base_executable',sys.executable)).resolve()):
            if any(w in ('-I','-E','-S') for w in words[1:]):deny('unguardable Python flags')
            if not env or str(guard) not in env.get('PYTHONPATH',''):deny('unguarded Python child')
            emit('guarded_python_child');return
        if resolved==trusted_git:
            rest=words[1:];location=Path(cwd or os.getcwd()).absolute()
            while rest and rest[0]=='-C':location=Path(rest[1]).absolute();rest=rest[2:]
            if not rest:deny('git without bounded operation')
            verb=rest[0]
            read={'rev-parse','ls-files','status','diff','show','ls-tree','log','cat-file','merge-base','check-ignore'}
            fixture={'init','add','commit','config','mv','tag','rm','switch','checkout'}
            if verb in read and not any(x in ('--ext-diff','--textconv') for x in rest):return
            # Fixture git writes are confined to this run's disposable home.
            if verb in fixture and location.is_relative_to(home):return
            deny('nonlocal or nonfixture git operation')
        if name in ('cmd','cmd.exe') and len(words)>=5 and words[1:3] in (['/c','mklink'],['/d','/c']):
            tail=words[2:] if words[1]=='/c' else words[3:]
            if tail[:2]==['mklink','/J'] and len(tail)==4:
                if all(Path(p).absolute().is_relative_to(home) and not any(c in p for c in '&|<>') for p in tail[2:]):return
        deny('unapproved external executable: '+name)
    sys.addaudithook(audit)
    sys.meta_path.insert(0,RestrictedImports())
    emit('guard_installed',python_guard=True)
    atexit.register(lambda:emit('guard_exit',violations=len(violations)))

