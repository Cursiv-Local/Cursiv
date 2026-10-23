"""Exact U82 user transcripts: policy, clean paths, provenance and failed tools."""
import pytest

from cursiv_engine.core import file_access as fs, grounding, turn_policy as tp


RESTRICTED = [
    'don’t inspect anything. how does photosynthesis work?',
    'just chat with me, no tools. explain the lightning 30-minute rule.',
    'don’t save any memories from this. my favorite color is blue.',
    'conversation only, do not retain this: the sample ID is NT-20261022-007.',
    'just talk — what is 2+2?',
    "Don't use any tools. Explain photosynthesis.",
    'Do not call plugins; just answer the question.',
    'For this turn, you must not inspect my files.',
    'You must not save any memories from this conversation.',
]


@pytest.mark.parametrize('text', RESTRICTED)
def test_exact_prefixes_are_conversation_only(text):
    assert tp.for_text(text) == tp.Policy(False, False, False, False)


@pytest.fixture
def pipeline(monkeypatch):
    from cursiv_engine.ui import chat_app as ca
    from cursiv_engine.core import netgate, phases, speed
    from test_netgate import _local_model
    _local_model(monkeypatch)
    monkeypatch.setattr(netgate, 'is_offline', lambda: True)
    monkeypatch.setattr(speed, 'battery_saver', lambda: True)
    monkeypatch.setattr(phases, '_connectivity', lambda *_: None)
    monkeypatch.setattr(ca, '_classify_message', lambda *_: 'chat')
    return ca


@pytest.mark.parametrize('provider', ['ollama', 'openai'])
@pytest.mark.parametrize('text', RESTRICTED)
def test_restrictions_precede_every_retrieval_and_retention(pipeline, monkeypatch, tmp_path, provider, text):
    from cursiv_engine.core import reference, calc, tools, notebook_tools, documents, presence, plugins, style, netgate
    from cursiv_engine.memory import intents, semantic
    ca = pipeline
    def denied(*a, **kw):
        pytest.fail('Restricted turn must not invoke retrieval, tools or retention')
    for module, names in [
        (reference, ['lookup', 'entries']), (calc, ['work_out_for_turn']), (tools, ['plan', 'run']),
        (notebook_tools, ['command']), (intents, ['command']), (fs, ['command']),
        (documents, ['library']), (presence, ['memory_state', 'settings']),
        (plugins, ['message_context']), (style, ['prompt_addendum']),
        (ca, ['_learn_later', '_build_strand_context', 'load_vault_context', '_load_session_ctx',
              '_call_openai_with_tools', '_verify_owner_code', '_strand_count', '_ref_available', '_codex_available']),
    ]:
        for name in names:
            monkeypatch.setattr(module, name, denied)
    captured = []
    def answer(messages, *a, **kw):
        captured.extend(messages)
        return iter(['We can discuss the question.\nSource: model knowledge (not checked against a source)'])
    monkeypatch.setattr(ca, '_call_ollama', answer)
    monkeypatch.setattr(ca, '_call_openai_direct', answer)
    if provider == 'openai':
        monkeypatch.setattr(netgate, 'allowed', lambda: True)  # mocked provider, no network
    before = list(tmp_path.iterdir())
    out = ''.join(ca.chat(text, [], '', None, file_access=True, root_path=str(tmp_path),
                          force_provider=provider, openai_key='dummy', replace_draft=True))
    assert 'This turn:' in out and 'memory saves disabled' in out
    assert 'Conversation history still follows' in out
    assert 'From Cursiv\'s offline reference' not in out and 'Checked on this computer' not in out
    assert not semantic.FACTS_FILE.exists() and list(tmp_path.iterdir()) == before
    if 'lightning' in text:
        assert 'unavailable in this turn' in out and captured == []
    else:
        system = '\n'.join(m['content'] for m in captured if m['role'] == 'system')
        assert 'inspection=False' in system and 'automatic retention=False' in system
        assert str(tmp_path) not in system
        assert out.count('Source: model knowledge') == 1  # application footer only
    assert tp.current() == tp.Policy()


def test_launcher_gates_before_notebook_or_memory_dispatch(monkeypatch):
    import chat_commands as cc
    monkeypatch.setattr(cc, 'notebook_command', lambda *a, **kw: pytest.fail('No notebook dispatch'))
    monkeypatch.setattr(cc, 'memory_command', lambda *a, **kw: pytest.fail('No memory dispatch'))
    for text in RESTRICTED:
        assert cc.handle_command(text, {}, []) is None


def test_restricted_file_request_is_denied_without_dispatch(pipeline, monkeypatch, tmp_path):
    monkeypatch.setattr(fs, 'command', lambda *a: pytest.fail('No file dispatch'))
    out = ''.join(pipeline.chat('No tools. file read secret.txt', [], '', None,
                               file_access=True, root_path=str(tmp_path)))
    assert 'memory saves disabled' in out and 'Checked on this computer' not in out


def test_readonly_workspace_and_read_summary_use_clean_paths(tmp_path):
    folder = tmp_path / 'launcher'
    folder.mkdir()
    path = folder / 'main.py'
    path.write_text('ENTRY_POINT_MARKER', encoding='utf-8')
    text = 'read only — look at the current workspace and tell me what’s there.'
    assert fs._parse(text, []) == ('list', '.', '')
    assert tp.for_text(text).inspect and not tp.for_text(text).change
    listed = fs.command(text, [], tmp_path)
    assert listed.receipts[0].ok and listed.receipts[0].path == str(tmp_path)
    for text in ['read the file launcher/main.py and summarize the entry point.',
                 'read the file "launcher/main.py" and summarize the entry point.']:
        assert fs._parse(text, []) == ('read', 'launcher/main.py', '')
        result = fs.command(text, [], tmp_path)
        assert result.receipts[0].path == str(path) and result.receipts[0].content == 'ENTRY_POINT_MARKER'


def test_literal_paths_and_payloads_remain_literal(tmp_path):
    filename = 'notes and summarize.txt'
    path = tmp_path / filename
    path.write_text('preserve', encoding='utf-8')
    assert fs.command('file read ' + filename, [], tmp_path).receipts[0].content == 'preserve'
    assert fs.command('read "' + filename + '" and summarize it.', [], tmp_path).receipts[0].content == 'preserve'
    result = fs.command('file create new.txt :: read only — no tools. and summarize everything.', [], tmp_path)
    assert result.receipts[0].ok
    assert (tmp_path / 'new.txt').read_text(encoding='utf-8') == 'read only — no tools. and summarize everything.'


@pytest.mark.parametrize('kind', ['tool', 'reference', 'calculation'])
def test_sources_use_application_evidence_not_model_footer(pipeline, monkeypatch, kind):
    ca = pipeline
    def inner(**kw):
        ca._set_answered('mock local model')
        if kind == 'tool':
            grounding.record_execution('list_folder authorized-workspace')
        elif kind == 'reference':
            ca._REF_SHOWN[:] = ['photosynthesis']
        else:
            from cursiv_engine.core import calc
            ca._WORKED = calc.work_out('what is 2+2?')
            assert ca._WORKED
        yield 'An answer.\n*[Source: model know'
        yield 'ledge (not checked against a source)]*'
    monkeypatch.setattr(ca, '_chat_inner', inner)
    reply = []
    out = ''.join(ca._chat_stream('a question', [], '', None, False, '', '', False, '', '', reply))
    assert 'model knowledge' not in out and out.count('Sources:') == 1


def test_provenance_resets_on_next_turn(pipeline, monkeypatch):
    ca = pipeline
    def inner(**kw):
        ca._set_answered('mock local model')
        if kw['message'] == 'first':
            grounding.record_execution('list_folder workspace')
        yield 'An answer.'
    monkeypatch.setattr(ca, '_chat_inner', inner)
    first = ''.join(ca._chat_stream('first', [], '', None, False, '', '', False, '', '', []))
    second = ''.join(ca._chat_stream('second', [], '', None, False, '', '', False, '', '', []))
    assert 'confirmed computer tool results' in first
    assert 'confirmed computer tool results' not in second and 'Source: model knowledge' in second


def test_source_text_inside_code_is_preserved(pipeline):
    code = '```text\nSource: sample data, not a status footer\n```\n'
    assert ''.join(pipeline._drop_fake_tool_lines(iter(code))) == code


def test_following_turn_restores_reference_and_calculation(pipeline, monkeypatch):
    from cursiv_engine.core import reference, calc
    reference_calls, calculation_calls = [], []
    monkeypatch.setattr(reference, 'lookup', lambda text: reference_calls.append(text) or [])
    monkeypatch.setattr(calc, 'work_out_for_turn', lambda text, history: calculation_calls.append(text))
    ''.join(pipeline.chat('Just talk. Explain photosynthesis.', [], '', None, force_provider='ollama'))
    assert not reference_calls and not calculation_calls
    ''.join(pipeline.chat('Explain photosynthesis.', [], '', None, force_provider='ollama'))
    assert reference_calls == ['Explain photosynthesis.'] and calculation_calls == ['Explain photosynthesis.']


def test_restriction_confirmation_survives_draft_replacement(pipeline, monkeypatch):
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **kw: iter(["I don't store anything."]))
    text = ''.join(pipeline.chat('Just talk about memory.', [], '', None, force_provider='ollama', replace_draft=True))
    final = text.rsplit(pipeline.REPLACE_SENTINEL, 1)[1]
    assert 'This turn:' in final and 'memory saves disabled' in final
    assert 'persistent local memory' in final


def test_failed_tool_suppresses_model_and_checker(pipeline, monkeypatch, tmp_path):
    from cursiv_engine.core import tools
    ca = pipeline
    monkeypatch.setattr(tools, 'might_need_tools', lambda _: True)
    monkeypatch.setattr(tools, 'plan', lambda *a: [dict(tool='list_folder', args={})])
    monkeypatch.setattr(tools, 'run', lambda *a, **kw: [tools.ToolOutcome('list_folder', 'PermissionError: denied')])
    monkeypatch.setattr(ca, '_call_ollama', lambda *a, **kw: pytest.fail('No model after denied tool'))
    monkeypatch.setattr(ca, '_router_llm', lambda *a, **kw: pytest.fail('No checking model after denied tool'))
    monkeypatch.setattr(ca, '_learn_later', lambda *a, **kw: pytest.fail('No learning from denied tool'))
    out = ''.join(ca.chat('what files can you see?', [], '', None, file_access=False,
                          root_path=str(tmp_path), force_provider='ollama'))
    assert 'Tool result unconfirmed' in out and 'PermissionError' in out
    assert 'no AI model' in out and 'Source: model knowledge' not in out


def test_relative_tool_paths_use_workspace_not_home(tmp_path, monkeypatch):
    from cursiv_engine.core import tools
    (tmp_path / 'notes.txt').write_text('WORKSPACE_MARKER', encoding='utf-8')
    monkeypatch.setattr(tools, '_resolve', lambda _: pytest.fail('No home-folder alias fallback'))
    results = tools.run([dict(tool='read_file', args=dict(path='notes.txt')),
                         dict(tool='list_folder', args=dict(path='.'))], root=tmp_path)
    assert all(r.ok for r in results)
    assert results[0].receipt['path'] == str(tmp_path / 'notes.txt')
    assert results[0].receipt['content'] == 'WORKSPACE_MARKER'
    assert 'WORKSPACE_MARKER' in tools.read_file('notes.txt', root=tmp_path)
    assert 'notes.txt' in tools.list_folder('.', root=tmp_path)
    assert 'notes.txt' in tools.find_files('notes', root=tmp_path)


@pytest.mark.parametrize('provider', ['openai', 'claude'])
def test_native_read_failure_stops_before_model_continuation(pipeline, monkeypatch, tmp_path, provider):
    import json
    from test_verified_filesystem import Response
    requests = []
    def request(req, **kw):
        requests.append(req)
        assert len(requests) == 1
        if provider == 'claude':
            return Response(dict(stop_reason='tool_use', content=[dict(type='tool_use', id='call-1',
                            name='read_file', input=dict(path='../outside.txt'))]))
        return Response(dict(choices=[dict(message=dict(role='assistant', content=None, tool_calls=[
                        dict(id='call-1', function=dict(name='read_file', arguments=json.dumps(dict(path='../outside.txt'))))]))]))
    monkeypatch.setattr(pipeline.urllib.request, 'urlopen', request)
    receipts = []
    if provider == 'claude':
        text = ''.join(pipeline._call_claude_with_tools([], 'dummy', tmp_path, on_action=receipts.append))
    else:
        text = ''.join(pipeline._call_openai_with_tools([], 'dummy', tmp_path, on_action=receipts.append))
    assert len(requests) == 1 and len(receipts) == 1 and not receipts[0].ok
    assert 'not confirmed' in text


@pytest.mark.parametrize('text', ['what can you do right now?', 'what’s your current workspace and file access status?'])
def test_operational_questions_are_native(pipeline, monkeypatch, tmp_path, text):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **kw: pytest.fail('No guessing operational state'))
    out = ''.join(pipeline.chat(text, [], '', None, file_access=True, root_path=str(tmp_path)))
    assert 'File access is on' in out and 'a particular operation still has to succeed' in out
    assert 'no AI model' in out


@pytest.mark.parametrize('replace', [True, False])
def test_detected_reference_dose_error_withdraws_model_instructions(pipeline, monkeypatch, replace):
    ca = pipeline
    def inner(**kw):
        ca._set_answered('mock local model')
        ca._REF_SHOWN[:] = ['water purification']
        yield 'Use 6 drops of 6% bleach per gallon.'
    monkeypatch.setattr(ca, '_chat_inner', inner)
    monkeypatch.setattr(ca, '_router_llm', lambda *a, **kw: pytest.fail('No model rewrite of reference safety'))
    monkeypatch.setattr(ca, '_learn_later', lambda *a, **kw: pytest.fail('No learning from withdrawn instructions'))
    text = ''.join(ca.chat('How much bleach per gallon?', [], '', None, replace_draft=replace))
    final = text.rsplit(ca.REPLACE_SENTINEL, 1)[1] if replace else text.split('Correction: ', 1)[1]
    assert 'draft conflicted' in final and 'withdrawn' in final
    assert 'Use 6 drops of 6%' not in final
    assert '8 drops of 6%' in final and 'not reviewed by a professional' in final
    assert 'Written by Cursiv, no AI model' in final and 'Answered by mock' not in final
