"""Own-source inventory, hash/version and authorization boundaries; no real user data."""
import json
import ast
from pathlib import Path
import pytest
from cursiv_engine.core import self_index as index, self_source, self_inspection, turn_policy
ROOT_FUNCTION = self_source.root


@pytest.fixture
def bundle(tmp_path,monkeypatch):
    sources={
        'cursiv_engine/core/sample.py':'from .other import helper\n\ndef query(sample):\n    return helper(sample)\n',
        'cursiv_engine/core/other.py':'def helper(value):\n    return value\n',
        'docs/CODE-MAP.md':'# Map\n- `core/sample.py` — sample lookup.\n',
    }
    for name,body in sources.items():
        p=tmp_path/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(body,encoding='utf-8')
    value=index.build(tmp_path,'test-version',paths=sources)
    manifest=tmp_path/index.NAME
    manifest.write_text(json.dumps(value),encoding='utf-8')
    monkeypatch.setattr(self_source,'root',lambda:tmp_path)
    monkeypatch.setattr(self_source,'version',lambda:'test-version')
    return tmp_path,value


def test_complete_symbols_and_imported_calls_are_indexed(bundle):
    root,value=bundle
    row=value['files']['cursiv_engine/core/sample.py']
    symbol=row['symbols'][0]
    assert symbol['name']=='query' and symbol['line']==3 and symbol['end']==4
    assert symbol['calls']==[dict(name='helper',line=4,target='cursiv_engine.core.other.helper')]
    assert index.load(root,'test-version')['snapshot']==value['snapshot']


def test_untracked_owner_documents_are_not_in_build_inventory(bundle,monkeypatch):
    root,value=bundle
    outside=root/'docs'/'untracked-owner-note.md'; outside.write_text('PRIVATE_MARKER')
    tracked='\0'.join(value['files'])+'\0'
    monkeypatch.setattr(index.subprocess,'check_output',lambda *a,**kw:tracked.encode())
    built=index.build(root,'test-version')
    assert 'docs/untracked-owner-note.md' not in built['files']
    assert all('PRIVATE_MARKER' not in json.dumps(row) for row in built['files'].values())


@pytest.mark.parametrize('name',['../outside.py','/outside.py','C:/private.py','docs/CURSIV-LEGAL-HANDOFF.md',
                                'field-notes.txt','test_internals/private.py','cursiv_engine/.cursiv/config.json',
                                'cursiv_engine/station/server.py','cursiv_engine/private/notes.md','docs/key.pem'])
def test_private_and_outside_names_cannot_become_own_source(name):
    assert not index.public_path(name)


def test_changed_source_is_not_reused_from_cache(bundle):
    root,value=bundle
    assert 'helper' in index.text(root,value,'cursiv_engine/core/sample.py')
    (root/'cursiv_engine/core/sample.py').write_text('def fabricated():\n    pass\n')
    with pytest.raises(ValueError,match='changed since indexing'):
        index.text(root,value,'cursiv_engine/core/sample.py')


def test_version_mismatch_and_modified_inventory_fail_closed(bundle):
    root,value=bundle
    with pytest.raises(ValueError,match='version'):
        index.load(root,'another-version')
    value['files']['cursiv_engine/core/sample.py']['sha256']='0'*64
    (root/index.NAME).write_text(json.dumps(value))
    with pytest.raises(ValueError,match='fingerprint'):
        index.load(root,'test-version')


def test_unknown_and_linked_source_cannot_be_read(bundle):
    root,value=bundle
    with pytest.raises(ValueError,match='inventory'):
        index.text(root,value,'docs/untracked-owner-note.md')
    path=root/'cursiv_engine/core/sample.py'
    target=root/'cursiv_engine/core/other.py'
    path.unlink()
    try:
        path.symlink_to(target)
    except OSError:
        pytest.skip('Symlink privilege unavailable')
    with pytest.raises(ValueError,match='Linked'):
        index.text(root,value,'cursiv_engine/core/sample.py')


def test_packaged_root_uses_bundle_not_workspace(bundle,monkeypatch):
    root,value=bundle
    monkeypatch.setattr(self_source,'root',ROOT_FUNCTION)
    import sys
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    monkeypatch.setattr(sys,'_MEIPASS',str(root),raising=False)
    monkeypatch.setattr(self_source,'version',lambda:'test-version')
    assert self_source.root()==root
    where,body=self_source.read('cursiv_engine/core/sample.py')
    assert 'test-version' in where and 'helper(sample)' in body


def test_mac_resources_hold_owned_source_without_following_framework_links(bundle,monkeypatch):
    import sys
    root,value=bundle
    contents=root/'Cursiv.app'/'Contents'
    resources=contents/'Resources'
    frameworks=contents/'Frameworks'
    frameworks.mkdir(parents=True)
    for name in (*value['files'],index.NAME):
        target=resources/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((root/name).read_bytes())
    monkeypatch.setattr(self_source,'root',ROOT_FUNCTION)
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    monkeypatch.setattr(sys,'_MEIPASS',str(frameworks),raising=False)
    monkeypatch.setattr(sys,'platform','darwin')
    assert self_source.root()==resources
    _,body=self_source.read('cursiv_engine/core/sample.py')
    assert 'helper(sample)' in body


def test_read_only_self_commands_still_honor_no_tools(bundle):
    with turn_policy.scope('No tools. Explain your code.'):
        assert self_source.files()==[]
        with pytest.raises(ValueError):
            self_source.read('cursiv_engine/core/sample.py')


def test_user_history_only_and_unrelated_turns_end_topic():
    q='And where does the model actually get called?'
    assert self_inspection.resolve(q,[dict(role='user',content='How do you process my messages?')])=='models'
    assert not self_inspection.resolve(q,[dict(role='assistant',content='How do you process my messages?')])
    assert not self_inspection.resolve(q,[dict(role='user',content='How do you process my messages?'),
                                         dict(role='user',content='What is a good lunch?')])
    assert not self_inspection.resolve('No tools. How do I cook rice?')
    previous=[dict(role='user',content='How does your notebook find a sample?')]
    assert not self_inspection.resolve('How do I record a new observation?',previous)
    assert not self_inspection.resolve('And what about the weather?',previous)


def test_index_build_is_deterministic(bundle):
    root,value=bundle
    second=index.build(root,'test-version',paths=value['files'])
    assert second==value


def test_git_newline_conversion_preserves_source_fingerprint(bundle):
    root,value=bundle
    path=root/'cursiv_engine/core/sample.py'
    original=path.read_bytes().replace(b'\r\n',b'\n')
    path.write_bytes(original.replace(b'\n',b'\r\n'))
    converted=index.build(root,'test-version',paths=value['files'])
    assert converted==value
    assert 'helper(sample)' in index.text(root,value,'cursiv_engine/core/sample.py')
    path.write_bytes(original.replace(b'return helper(sample)',b'return 9'))
    with pytest.raises(ValueError,match='changed since indexing'):
        index.text(root,value,'cursiv_engine/core/sample.py')


def test_same_named_local_imports_do_not_cross_link():
    text=('def first():\n    from .one import helper\n    return helper()\n'
          'def second():\n    from .two import helper\n    return helper()\n')
    module,symbols=index._parse('cursiv_engine/core/sample.py',text)
    assert symbols[0]['calls'][0]['target']=='cursiv_engine.core.one.helper'
    assert symbols[1]['calls'][0]['target']=='cursiv_engine.core.two.helper'


def test_a_parameter_does_not_link_to_same_named_global_function():
    text='def helper():\n    pass\ndef example(helper):\n    return helper()\n'
    module,symbols=index._parse('cursiv_engine/core/sample.py',text)
    assert symbols[1]['calls'][0]['target']==''
    assert symbols[1]['name']=='example'


def test_installed_inventory_declaration_names_match_actual_source():
    root=ROOT_FUNCTION()
    value=index.load(root,self_source.version())
    for path,row in value['files'].items():
        if not row['symbols']:
            continue
        tree=ast.parse(index.text(root,value,path))
        real={(n.lineno,n.name) for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
        for symbol in row['symbols']:
            assert (symbol['line'],symbol['name'].split('.')[-1]) in real, (path,symbol)


def test_top_level_malformed_inventory_is_reported_cleanly(bundle):
    root,value=bundle
    (root/index.NAME).write_text('[]')
    with pytest.raises(ValueError,match='version'):
        index.load(root,'test-version')


@pytest.mark.parametrize('question',[
    'How do you handle an insulin overdose?',
    'How do you help with chest pain?',
    'What is your current model?',
    'Inspect my repository for notebook retrieval code.',
])
def test_safety_model_identity_and_user_code_keep_existing_routes(question):
    assert not self_inspection.resolve(question)


@pytest.mark.parametrize('question',[
    'What can Cursiv do?',
    "What are Cursiv's main features?",
    'What is your current workspace?',
    'What do you remember about East Fork?',
    'How does Cursiv save files?',
    'How does Cursiv memory work?',
    'Does Cursiv work offline?',
])
def test_feature_help_status_and_personal_recall_stay_native(question):
    assert not self_inspection.resolve(question)


def test_alternate_line_reference_must_be_present_in_evidence():
    packet=self_inspection.Packet('source','test','snapshot',(
        self_inspection.Snippet('cursiv_engine/core/example.py','example',(3,4),'3: def example():\n4:     return 1','hash'),))
    token=self_inspection._active.set(packet)
    try:
        assert not self_inspection.problems('In `example.py`, line 3, `example()` is declared.')
        assert self_inspection.problems('In `example.py`, line 99, `example()` is declared.')
        assert self_inspection.problems('See cursiv_engine/core/example.py:99.')
        assert self_inspection.problems('This is the only function that reads records.')
    finally:
        self_inspection._active.reset(token)


def test_correction_context_includes_real_append_operations():
    token=self_inspection._active.set(None)
    try:
        packet=self_inspection.prepare('Do you replace my original notebook reading when I correct it? Explain your implementation.')
        assert packet and not packet.error
        supplied=packet.prompt()
        assert 'corrects=entry_id' in supplied
        assert 'text + line' in supplied
        assert '.open("a"' in '\n'.join(s.text for s in packet.snippets)
    finally:
        self_inspection._active.reset(token)


def test_nested_callback_operations_are_not_parent_execution_facts():
    text='def send():\n    def later():\n        return _run_turn("confirmed")\n    return _chat_stream("now")\n'
    _,symbols=index._parse('cursiv_engine/core/example.py',text)
    parent=next(s for s in symbols if s['name']=='send')
    facts=self_inspection._structure('cursiv_engine/core/example.py',parent,text.splitlines(),'pipeline')
    assert facts and '_chat_stream' in json.dumps(facts)
    assert '_run_turn' not in json.dumps(facts)


def test_read_only_command_recursion_retains_its_confirmation_guard():
    token=self_inspection._active.set(None)
    try:
        packet=self_inspection.prepare('How do you process my messages?')
        assert packet and not packet.error
        fact=next(f for f in packet.observations if f['symbol']=='ChatPanel._run_turn' and '_run_turn' in f.get('statement',''))
        assert 'proposal.ok and (not proposal.needs_confirm)' in fact['when']
    finally:
        self_inspection._active.reset(token)
