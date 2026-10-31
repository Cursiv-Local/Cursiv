"""Strict-offline collection exclusions and unexpected-attempt accounting."""
import ast
import json
from pathlib import Path
import re
import pytest
import offline_guard as guard

EXCLUDED={
 'test_self_knowledge_live.py':'requires live model inference',
 'test_network_isolation_process.py':'requires a real loopback HTTP server',
 'test_offline_process.py':'isolated -I subprocess and real loopback assertions',
 'test_plugin_isolation.py':'isolated -I worker cannot inherit this guard',
 'test_persistence.py':'contains an intentional real connectivity probe',
 'test_phone_receive.py':'requires a real local HTTP receiver',
}
exclusions=[]
unsafe={}
def pytest_ignore_collect(collection_path,config):
    path=Path(str(collection_path))
    if path.name.startswith('test_station'):
        exclusions.append(dict(path=path.name,reason='Field Station excluded by owner'));return True
    if path.name in EXCLUDED:
        exclusions.append(dict(path=path.name,reason=EXCLUDED[path.name]));return True
    return None

def pytest_collection_modifyitems(config,items):
    plugin_workers={'test_approved_plugin_runs','test_plugin_changed_after_approval_does_not_load','test_switched_off_plugin_does_not_run'}
    for item in items:
        path=Path(str(item.path))
        if path.name=='test_strict_offline_guard.py':continue  # operations are enclosed in explicit expected-denial checks
        if path not in unsafe:
            text=path.read_text(encoding='utf-8-sig');tree=ast.parse(text);blocked={}
            functions={n.name:n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
            for name,node in functions.items():
                body=ast.get_source_segment(text,node) or ''
                calls=[n for n in ast.walk(node) if isinstance(n,ast.Call)]
                if re.search(r"['\"]-I['\"]|['\"]-S['\"]",body):blocked[name]='isolated Python child bypasses startup guard'
                elif any(isinstance(n.func,ast.Attribute) and n.func.attr in ('bind','listen','serve_forever') for n in calls):blocked[name]='requires a real socket server'
                elif 'subprocess.' in body and re.search(r'\bNODE\b|[\x27\"]node(?:\.exe)?[\x27\"]',body):blocked[name]='Node child networking cannot be guarded by Python hooks'
            for _ in range(len(functions)):
                for name,node in functions.items():
                    if name in blocked:continue
                    used={n.func.id for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}|{a.arg for a in node.args.args}
                    hit=next((n for n in used if n in blocked),None)
                    if hit:blocked[name]=blocked[hit]
            unsafe[path]=blocked
        reason=unsafe[path].get(getattr(item,'originalname',None) or item.name.split('[',1)[0])
        if path.name=='test_core.py' and item.name in plugin_workers:reason='plugin worker uses isolated -I Python' 
        if item.nodeid.startswith(('tests/test_netgate.py::test_closed_gate_still_allows_loopback','tests/test_netgate.py::test_closed_gate_refuses_connections_at_the_socket')):
            reason='exercises OS socket calls; application-level mocked enforcement is tested separately'
        if item.nodeid=='tests/test_problem_report.py::test_nothing_is_sent_in_offline_mode':
            reason='expects real socket-level offline rejection; no socket calls authorized'
        if reason:
            item.add_marker(pytest.mark.skip(reason='strict offline: '+reason))
            exclusions.append(dict(path=item.nodeid,reason=reason))

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):guard.current_test=item.nodeid

@pytest.hookimpl(wrapper=True,trylast=True)
def pytest_runtest_teardown(item,nextitem):
    yield
    bad=[kind for test,kind in guard.violations if test==item.nodeid]
    if bad:pytest.fail('Unexpected operations blocked by offline guard: '+', '.join(bad),pytrace=False)

@pytest.fixture(autouse=True)
def disable_native_browser_launch(monkeypatch):
    try:
        from PyQt6.QtGui import QDesktopServices
        monkeypatch.setattr(QDesktopServices,'openUrl',lambda *a,**k:guard.deny('native browser launch'))
    except ImportError:pass

def pytest_sessionfinish(session,exitstatus):
    import os
    Path(os.environ['CURSIV_STRICT_EXCLUSIONS']).write_text(json.dumps(exclusions,indent=2)+'\n',encoding='utf-8')
    if guard.violations:session.exitstatus=1


@pytest.fixture(autouse=True)
def synthetic_unavailable_startup_probes(monkeypatch):
    # Older GUI tests instantiate live discovery widgets. Model response tests
    # still provide their own adapters; this only supplies absent-service state.
    from cursiv_engine.chat import status
    from cursiv_engine.ui import chat_app
    monkeypatch.setattr(status,'local_models',lambda *a,**kw:None)
    monkeypatch.setattr(chat_app,'_ollama_running',lambda:False)
    monkeypatch.setattr(chat_app,'_ensure_ollama',lambda:False)
    monkeypatch.setattr(chat_app,'_ollama_tags',lambda:None)
    monkeypatch.setattr(chat_app,'_is_online',lambda:False)

    from cursiv_engine.core import ollama_host,speed
    monkeypatch.setattr(ollama_host,'running',lambda *a,**kw:False)
    monkeypatch.setattr(speed,'loaded_models',lambda:[])
