"""Independent structure checks, not model assertions about plausible filenames."""
import ast
import json
from pathlib import Path
import pytest
from cursiv_engine.core import self_index, self_source, self_inspection as own, source_analysis as analysis

def test_conditional_module_import_and_local_shadow_targets():
    code=('try:\n from cursiv_engine.ui.chat_app import chat as generate\nexcept ImportError:\n pass\n'
          'def send():\n return generate("hi")\n'
          'def other(generate):\n return generate("hi")\n')
    _,symbols=self_index._parse('launcher/example.py',code)
    assert symbols[0]['calls'][0]['target']=='cursiv_engine.ui.chat_app.chat'
    assert symbols[1]['calls'][0]['target']==''

def test_conflicting_import_targets_are_unknown_not_last_branch_wins():
    code='if condition:\n from .one import call\nelse:\n from .two import call\ndef send():\n return call()\n'
    _,symbols=self_index._parse('cursiv_engine/core/example.py',code)
    assert symbols[0]['calls'][0]['target']==''

def test_nested_function_target_is_lexical_not_same_named_global():
    code='def later():\n pass\ndef parent():\n def later():\n  pass\n return later()\n'
    _,symbols=self_index._parse('cursiv_engine/core/example.py',code)
    parent=next(s for s in symbols if s['name']=='parent')
    assert parent['calls'][0]['target']=='cursiv_engine.core.example.parent.later'

def test_pipeline_roles_are_actual_ast_declarations_and_build_guard():
    packet=own.prepare('Trace what happens when I submit a message in Cursiv.')
    assert packet and not packet.error
    roles={r['role']:r for r in packet.analysis['roles']}
    expected={'application startup','UI initialization','message input handler','request routing',
              'native tool dispatch','local model transport','response verification coordinator','UI output rendering'}
    assert expected<=roles.keys()
    for role,r in roles.items():
        raw=(self_source.root()/r['path']).read_text(encoding='utf-8-sig')
        _,symbols=self_index._parse(r['path'],raw)
        assert any(s['name']==r['symbol'] and s['line']==r['line'] for s in symbols),role
    startup=roles['application startup']
    assert startup['path']=='launcher/main.py' and startup['symbol']=='main'
    assert startup['build_path']=='launcher/build.spec'

def test_cross_file_alias_and_explicit_runtime_service_edges():
    packet=own.prepare('Trace what happens when I submit a message in Cursiv.')
    edges=packet.analysis['edges']
    assert any(e['symbol']=='ChatPanel._run_turn' and e['target_path']=='cursiv_engine/ui/chat_app.py' and e['target_symbol']=='chat' for e in edges)
    assert any(e['path']=='cursiv_engine/ui/chat_app.py' and e['target_path']=='cursiv_engine/chat/completion.py' for e in edges)
    assert any('facade service' in e['kind'] for e in edges)
    assert any(e['symbol']=='ChatPanel._send' and e['target_symbol']=='ChatPanel._run_turn' and 'callback' in e['kind'] for e in edges)
    for e in edges:
        text=(self_source.root()/e['path']).read_text(encoding='utf-8-sig')
        assert e['expression'] in text.split('\n')[e['line']-1]

def test_unicode_separator_in_literal_does_not_shift_source_citations(tmp_path):
    rel='cursiv_engine/core/example.py';p=tmp_path/rel;p.parent.mkdir(parents=True)
    p.write_text('text="before\u2028after"\ndef run():\n return len(text)\n',encoding='utf-8')
    index=self_index.build(tmp_path,'test',paths=[rel])
    record=analysis.Session(tmp_path,index).symbol(rel,'run')
    assert record['line']==2 and '2: def run()' in record['excerpt']
    assert record['calls'][0]['line']==3
    assert self_source.source_lines('one\r\ntwo\rthree\u2028four')==['one','two','three\u2028four']

def test_prompt_is_bounded_and_discloses_other_namespaces():
    p=own.prepare('Inspect your Field Copy implementation for copying portable workspaces to an external SSD.')
    assert p and not p.error
    assert len(p.prompt().encode())<=4900
    assert set(p.coverage['unread_scopes'])=={'authorized_workspace','imported_documents','external_field_copy','runtime_configuration'}
    assert p.coverage['successful_reads']<=24 and p.coverage['tool_calls']<=48

@pytest.mark.parametrize('pattern',['(a+)+$','(?P<secret>.*)','[a-z]{999999999,}'])
def test_complex_regex_is_not_executed(pattern):
    facts=analysis.technical(f'Check the regex `{pattern}` against `page`.',{})
    assert facts and facts[0]['status']=='UNKNOWN' and 'matched' not in facts[0]

def test_regex_results_do_not_establish_presence_in_application_source():
    facts=analysis.technical('Regex `[A-Z_]{2,5}` on `page` and `PAGE`.',{})
    assert [f['matched'] for f in facts]==[False,True]
    assert all(not f['pattern_in_inspected_source'] for f in facts)

def test_changed_file_cannot_reuse_verified_ast_cache(tmp_path):
    rel='cursiv_engine/core/example.py';p=tmp_path/rel;p.parent.mkdir(parents=True);p.write_text('def run():\n return 1\n')
    index=self_index.build(tmp_path,'test',paths=[rel])
    assert analysis.Session(tmp_path,index).symbol(rel,'run')
    p.write_text('def run():\n return 2\n')
    session=analysis.Session(tmp_path,index)
    assert session.symbol(rel,'run') is None and session.errors

def test_plausible_but_forged_symbol_metadata_cannot_become_verified(tmp_path):
    rel='cursiv_engine/core/example.py';p=tmp_path/rel;p.parent.mkdir(parents=True);p.write_text('def run():\n return 1\n')
    index=self_index.build(tmp_path,'test',paths=[rel]);index['files'][rel]['symbols'][0]['name']='invented'
    assert analysis.Session(tmp_path,index).symbol(rel,'invented') is None

def test_inspection_absence_and_invented_functions_have_distinct_states():
    p=own.prepare('Trace what happens when I submit a message in Cursiv.')
    assert analysis.claim_issues(p.analysis,'The route is cursiv_engine/chat/completion.py::fabricated.')
    assert analysis.claim_issues(p.analysis,'The route is cursiv_engine/chat/completion.py:1-999999.')
    assert analysis.claim_issues(p.analysis,'VERIFIED: PDFs cannot be processed.')
    assert not analysis.claim_issues(p.analysis,'UNKNOWN: not found in the searched scope; missing evidence does not establish absence.')

def test_source_unavailable_never_substitutes_workspace(tmp_path,monkeypatch):
    monkeypatch.setattr(self_source,'root',lambda:tmp_path)
    p=own.prepare('Inspect your source code.')
    assert p is not None and p.status=='UNKNOWN' and 'No workspace substitution' in p.error

def test_audit_is_hypothesis_not_a_confirmed_defect():
    p=own.prepare('Perform a read-only self-audit of your response pipeline.')
    finding=p.analysis['audit']
    assert finding['status'] in ('INFERRED','UNKNOWN')
    if finding['status']=='INFERRED':
        assert finding['confirmed_defect'] is False
        assert all(finding.get(k) for k in ('path','symbol','line','trigger','reproduction','minimal_fix','regression'))
        answer=analysis.native(p.analysis,'audit')
        assert 'INFERRED reliability hypothesis' in answer and 'not a reproduced defect' in answer
        assert 'Reproduce:' in answer and 'Regression test:' in answer

def test_transport_timeout_and_retry_are_ast_witnessed():
    p=own.prepare('What happens if Ollama times out?')
    t=p.analysis['transport']
    raw=(self_source.root()/t['path']).read_text(encoding='utf-8-sig').split('\n')
    assert 'open_request' in raw[t['line']-1] and 'timeout=600' in raw[t['line']-1]
    answer=analysis.native(p.analysis,'models')
    assert 'retry' in answer and 'timeout=600' in answer and 'not every caller' in answer

def test_capability_denial_guard_does_not_reject_permission_limit():
    p=own.prepare('Inspect your file access restrictions in code.')
    assert not analysis.claim_issues(p.analysis,'No user workspace was read; source inspection cannot modify a workspace.')
    assert analysis.claim_issues(p.analysis,'Cursiv does not support portable workspaces.')
    assert analysis.claim_issues(p.analysis,'All operations use encrypted, vault-protected paths.')

def test_portable_rules_fail_closed_when_a_required_copy_witness_changes():
    p=own.prepare('Inspect your Field Copy implementation for copying portable workspaces to an external SSD.')
    assert p.analysis['portable_contract']
    answer=analysis.native(p.analysis,'portable')
    assert 'include_private' in answer and 'No external drive' in answer
    index=self_index.load(self_source.root(),self_source.version())
    session=analysis.Session(self_source.root(),index)
    session.read('launcher/usb_ops.py')
    tree,nodes,symbols,module=session.syntax['launcher/usb_ops.py']
    nodes=dict(nodes,copy_files=ast.parse('def copy_files():\n pass').body[0])
    session.syntax['launcher/usb_ops.py']=(tree,nodes,symbols,module)
    assert analysis._portable_contract(session) is None
    assert analysis.native(dict(p.analysis,portable_contract=None),'portable').startswith('UNKNOWN:')

def test_source_analysis_does_not_write_or_call_network(monkeypatch):
    import urllib.request
    monkeypatch.setattr(Path,'write_text',lambda *a,**k:pytest.fail('Inspection must not write'))
    monkeypatch.setattr(Path,'write_bytes',lambda *a,**k:pytest.fail('Inspection must not write'))
    monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**k:pytest.fail('No inspection network'))
    packet=own.prepare('Perform a read-only self-audit of your response pipeline.')
    assert packet and packet.coverage['successful_reads']>0

def test_permission_failure_is_distinct_from_missing_source(monkeypatch):
    def denied(*args):raise PermissionError('Synthetic source permission denial')
    monkeypatch.setattr(self_index,'text',denied)
    packet=own.prepare('Locate the PDF importer in your installed code.')
    assert packet.status=='ACCESS DENIED' and packet.coverage['successful_reads']==0

def test_seen_holdout_regex_wording_initiates_deterministic_check():
    p=own.prepare('Inspect your regex logic: does `[A-Z_]{2,5}` fully match `page`, and does it fully match `PAGE`?')
    assert p and p.topic=='regex' and p.coverage['successful_reads']>0
    assert [f['matched'] for f in p.technical]==[False,True]

def test_memory_storage_explanation_checks_read_before_backup():
    p=own.prepare('Find the code that stores and retrieves your persistent memory.')
    assert p.analysis['memory_contract']
    answer=analysis.native(p.analysis,'memory')
    assert 'before backing them up' in answer and 'No saved facts' in answer
    session=analysis.Session(self_source.root(),self_index.load(self_source.root(),self_source.version()))
    session.read('cursiv_engine/memory/semantic.py')
    tree,nodes,symbols,module=session.syntax['cursiv_engine/memory/semantic.py']
    nodes=dict(nodes,_write_facts=ast.parse('def _write_facts():\n _backup_existing()\n _facts,bad=_read_facts()').body[0])
    session.syntax['cursiv_engine/memory/semantic.py']=(tree,nodes,symbols,module)
    assert analysis._memory_contract(session) is None

@pytest.mark.parametrize('question,topic,required',[
    ('Trace your Field Notebook creation, correction and verification code.','notebook','stored original'),
    ('Trace your document search implementation.','documents','BM25-style'),
    ('Find the code that verifies your responses.','verification','does not prove every statement is true'),
])
def test_critical_feature_rules_are_checked_and_do_not_certify_runtime(question,topic,required):
    p=own.prepare(question)
    assert p and p.analysis['feature_rules']
    answer=analysis.native(p.analysis,topic)
    assert required in answer and 'static rules conditional' in answer
    assert analysis.native(dict(p.analysis,feature_rules=None),topic).startswith('UNKNOWN:')

def test_notebook_verification_rule_detects_changed_hash_check():
    session=analysis.Session(self_source.root(),self_index.load(self_source.root(),self_source.version()))
    path='cursiv_engine/core/fieldlog.py';session.read(path)
    assert analysis._feature_rules(session,'notebook')
    tree,nodes,symbols,module=session.syntax[path]
    nodes=dict(nodes,verify=ast.parse('def verify():\n return []').body[0])
    session.syntax[path]=(tree,nodes,symbols,module)
    assert analysis._feature_rules(session,'notebook') is None

def test_desktop_dispatch_does_not_query_memory_for_source_question(monkeypatch):
    import chat_commands
    monkeypatch.setattr(chat_commands,'memory_command',lambda *a,**k:pytest.fail('No private-memory lookup for source analysis'))
    assert chat_commands.handle_command('Find the code that stores and retrieves your persistent memory.',{},[]) is None

@pytest.mark.parametrize('question',['Find your memories about Willow Basin.','Inspect your notebook entries.',
    'Find all notebook entries for sample WB-107.','Import a PDF document.','Copy my workspace to the SSD.'])
def test_source_intent_does_not_capture_data_or_copy_operations(question):
    assert own.resolve(question)==''
