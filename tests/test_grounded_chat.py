"""Boundary, operational state, dated recall and source-grounding regressions."""
from datetime import date
import json
import os
import subprocess
import sys

import pytest

from cursiv_v215.core import grounding, presence, turn_policy as tp
from cursiv_v215.memory import intents as mi, recall, semantic as sem


def write_records(records):
    sem.FACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    sem.FACTS_FILE.write_text('\n'.join(json.dumps(r) for r in records) + '\n', encoding='utf-8')


def record(ident='M-81', when='2026-10-22 00:40', **kw):
    return dict(id=ident, text='My field site is North Ridge.', created=when, person='dana', **kw)


def test_scope_resets_on_generator_close_and_exception():
    @tp.scoped
    def run(message):
        assert not tp.current().inspect
        yield 'one'
        raise RuntimeError('done')
    gen = run('Just talk.')
    assert next(gen) == 'one'
    gen.close()
    assert tp.current() == tp.Policy()
    with pytest.raises(RuntimeError):
        list(run('Just talk.'))
    assert tp.current() == tp.Policy()
    with tp.scope('No tools'):
        with tp.scope('Read source.py'):
            assert not tp.current().inspect
    assert tp.current() == tp.Policy()


def test_native_provider_executor_cannot_bypass_current_limits(tmp_path):
    from cursiv_v215.ui import chat_app as ca
    path = tmp_path / 'existing.txt'
    path.write_text('original', encoding='utf-8')
    with tp.scope('Just talk about the files'):
        assert not ca._file_tool_result('read_file', dict(path=str(path)), tmp_path).ok
        assert not ca._file_tool_result('create_file', dict(path='new.txt', content='no'), tmp_path).ok
        assert 'No action' in ca.execute_tool('system_info', {}, tmp_path)
    assert path.read_text() == 'original' and not (tmp_path / 'new.txt').exists()


def test_readonly_context_prevents_legacy_memory_repair(monkeypatch):
    write_records([record()])
    before = sem.FACTS_FILE.read_bytes()
    monkeypatch.setattr(sem, 'repair_learned', lambda *_: pytest.fail('Read-only must not migrate'))
    with tp.scope('Read-only review'):
        assert sem.list_facts('dana')
        assert not mi.execute(mi.Action(mi.SAVE, content='not authorized'), person='dana').ok
    assert sem.FACTS_FILE.read_bytes() == before


def test_launcher_constraints_defer_to_guarded_conversation(monkeypatch):
    import chat_commands as cc
    monkeypatch.setattr(cc, '_strand_save', lambda *_: pytest.fail('No save'))
    assert cc.handle_command("save this but don't save anything", {}, []) is None


@pytest.mark.parametrize('enabled', [True, False])
def test_state_uses_explicit_session_grant_and_memory_setting(monkeypatch, tmp_path, enabled):
    sem.set_learning(False)
    write_records([record(), record('other', person_unused='ignored') | dict(person='someone_else')])
    monkeypatch.setattr(sem, 'repair_learned', lambda *_: pytest.fail('Status must not migrate'))
    state = presence.snapshot(str(tmp_path), enabled, person='dana')
    assert state['file_access'] is enabled
    assert state['authorized_workspace'] == (str(tmp_path) if enabled else None)
    assert state['memory']['active_records'] == 1
    assert state['memory']['automatic_learning'] is False
    assert presence.snapshot()['file_access'] is None
    answer = presence.state_answer(state)
    assert ('File access is on' if enabled else 'File access is off') in answer
    assert 'across restarts' in answer and 'retraining' in answer and 'while closed' in answer


def test_damaged_memory_setting_is_unknown_not_reset():
    sem.SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    sem.SETTINGS_FILE.write_text('{"learn":"false"}', encoding='utf-8')
    before = sem.SETTINGS_FILE.read_bytes()
    status = presence.memory_state('dana')
    assert status['automatic_learning'] is None and status['errors']
    assert sem.SETTINGS_FILE.read_bytes() == before


@pytest.mark.parametrize('provider', ['', 'ollama', 'openai', 'grok', 'claude'])
def test_live_status_is_native_with_no_model_or_workspace_scan(monkeypatch, tmp_path, provider):
    from cursiv_v215.ui import chat_app as ca
    from cursiv_v215.core import tools
    monkeypatch.setattr(ca, '_chat_inner', lambda **_: pytest.fail('No model'))
    monkeypatch.setattr(tools, 'plan', lambda *_: pytest.fail('No planner'))
    monkeypatch.setattr(tools, 'list_folder', lambda *_: pytest.fail('No scan'))
    reply = ''.join(ca.chat(
        'Based on your current operational state, am I offline? Can you read or write workspace files right now? '
        'Can you observe anything while Cursiv is closed?', [
            dict(role='assistant', content='I cannot write files and have no persistent memory.')],
        '', None, file_access=True, root_path=str(tmp_path), force_provider=provider))
    assert 'File access is on' in reply and str(tmp_path) in reply
    assert 'persistent local memory' in reply and 'cannot observe' in reply


def test_hypotheticals_remain_conversational():
    assert not presence.answers_state_question('If I erased your memories, would you still be the same Cursiv?')
    assert not presence.answers_state_question('Explain self-awareness and persistent memory.')


def test_prompt_retains_current_capabilities_without_forcing_subjective_awareness(tmp_path):
    state = presence.snapshot(str(tmp_path), True, person='dana')
    prompt = presence.prompt('dana', observed=state)
    assert '"file_access": true' in prompt
    assert 'does not retrain' in prompt and 'speculation' in prompt
    presence.configure('dana', context=False)
    assert presence.prompt('dana', observed=state) == ''


@pytest.mark.parametrize('word', ['past', 'passed', 'last'])
@pytest.mark.parametrize('amount', ['2', 'two'])
def test_natural_temporal_recall_is_native_and_bounded(monkeypatch, word, amount):
    monkeypatch.setattr(recall, 'today', lambda: date(2026, 10, 22))
    write_records([record('start', '2026-10-09 00:00'), record('end'),
                   record('old', '2026-10-08 23:59'), record('future', '2026-10-23 00:00'),
                   record('other') | dict(person='other'),
                   record('superseded') | dict(status='superseded'),
                   record('unknown', 'not a date')])
    before = sem.FACTS_FILE.read_bytes()
    result = mi.command(f'what do you remember from the {word} {amount} weeks', [], person='dana',
                        classifier=lambda *_: pytest.fail('No model classifier'))
    assert result.ok and [r['id'] for r in result.outcomes[0].records] == ['start', 'end']
    assert '2026-10-09 through 2026-10-22' in result.render()
    assert 'no usable saved date' in result.render() and 'complete conversation archive' in result.render()
    assert sem.FACTS_FILE.read_bytes() == before


@pytest.mark.parametrize('text', [
    'what do you remember from last month',
    'what do you remember from 2026-10-25 to 2026-10-01',
    'what do you remember from past 0 days',
    'what do you remember from between 2026-02-30 and 2026-10-22',
])
def test_unresolved_dates_clarify_instead_of_generating_history(text):
    result = mi.command(text, [], person='dana', classifier=lambda *_: pytest.fail('No classifier'))
    assert result is not None and not result.ok and 'clarification' in result.render()


def test_recall_today_yesterday_range_timezone_and_missing_date(monkeypatch):
    monkeypatch.setattr(recall, 'today', lambda: date(2026, 10, 22))
    assert recall.window('today') == (date(2026, 10, 22),) * 2
    assert recall.window('yesterday') == (date(2026, 10, 21),) * 2
    assert recall.window('between 2026-10-01 and 2026-10-02') == (date(2026, 10, 1), date(2026, 10, 2))
    assert recall.saved_day(dict(created='2026-10-22')) == date(2026, 10, 22)
    assert recall.saved_day(dict(date='2026-10-21')) == date(2026, 10, 21)
    assert recall.saved_day(dict(created='garbage')) is None
    assert recall.saved_day(dict(created='2026-10-22T12:00:00+00:00')) is not None


def test_recall_empty_error_and_bounded_output(monkeypatch):
    monkeypatch.setattr(recall, 'today', lambda: date(2026, 10, 22))
    result = mi.execute(mi.Action(mi.RECALL, period='past two weeks'), person='dana')
    assert result.ok and 'No matching' in result.message and 'never discussed' in result.message
    write_records([record(str(i)) for i in range(45)])
    result = mi.execute(mi.Action(mi.RECALL, period='past two weeks'), person='dana')
    assert len(result.records) == 40 and result.message.startswith('45 matching saved memory records')
    assert 'showing 40' in result.message
    monkeypatch.setattr(sem, '_read_facts', lambda: (_ for _ in ()).throw(PermissionError('denied')))
    failed = mi.execute(mi.Action(mi.RECALL, period='past two weeks'), person='dana')
    assert not failed.ok and 'storage error' in failed.message
    assert 'No matching' not in failed.message


def test_recall_is_readonly_despite_unreadable_lines_and_settings():
    write_records([record()])
    with sem.FACTS_FILE.open('a', encoding='utf-8') as f:
        f.write('damaged line\n')
    sem.SETTINGS_FILE.write_text('not JSON', encoding='utf-8')
    before = (sem.FACTS_FILE.read_bytes(), sem.SETTINGS_FILE.read_bytes())
    result = mi.command('what do you remember about North Ridge?', [], person='dana')
    assert result.ok and 'North Ridge' in result.render()
    assert 'remain in the original file' in result.render()
    assert not (sem.FACTS_FILE.parent / sem.UNREADABLE_FILE_NAME).exists()
    assert (sem.FACTS_FILE.read_bytes(), sem.SETTINGS_FILE.read_bytes()) == before


def test_dated_recall_survives_a_fresh_python_process(tmp_path, monkeypatch):
    # A Windows pipe may default to cp1252; this reader explicitly expects UTF-8.
    monkeypatch.setenv('PYTHONIOENCODING', 'cp1252')
    saved = mi.command('remember My restart marker is GROUNDED-821.', [], person='dana')
    ident = saved.outcomes[0].records[0]['id']
    script = (
        "import sys; from pathlib import Path; from cursiv_v215.memory import intents,semantic as s;"
        "s.FACTS_FILE=Path(sys.argv[1]);s.SETTINGS_FILE=Path(sys.argv[2]);"
        "r=intents.command('what do you remember from past 14 days',[],person='dana');"
        "assert r.ok; print(r.render())")
    ran = subprocess.run([sys.executable, '-B', '-c', script, str(sem.FACTS_FILE), str(sem.SETTINGS_FILE)],
                         capture_output=True, text=True, encoding='utf-8', check=True,
                         env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    assert 'GROUNDED-821' in ran.stdout and ident in ran.stdout


@pytest.mark.parametrize('provider', ['ollama', 'openai', 'grok', 'claude'])
def test_dated_recall_cannot_be_transferred_to_model(monkeypatch, provider):
    from cursiv_v215.ui import chat_app as ca
    monkeypatch.setattr(ca, '_chat_inner', lambda **_: pytest.fail('No model'))
    reply = ''.join(ca.chat('what do you remember from the passed 2 weeks', [], '', None, force_provider=provider))
    assert reply.startswith('0 matching saved memory records') and 'No matching' in reply


def test_source_history_is_a_hint_not_proof_and_rechecks_authorization(tmp_path):
    path = tmp_path / 'presence.py'
    path.write_text('def settings():\n    return {"context": True}\n', encoding='utf-8')
    hint = dict(operation='read_file', path=str(path), content='invented quote', ok=True)
    history = [dict(role='assistant', content='I read it.', file_receipts=[hint])]
    @grounding.scoped
    def run():
        results = grounding.refresh_history('Quote the settings function source', history, tmp_path)
        assert results[0].ok
        ctx = grounding.source_context()
        assert 'return' in ctx and 'invented quote' not in ctx
        with tp.scope('Just talk; do not inspect documents'):
            assert grounding.refresh_history('Quote the source', history, tmp_path) == []
        yield ctx
    assert str(path) in ''.join(run()).replace('\\\\', '\\')
    assert grounding.source_context() == ''
    bad = [dict(role='assistant', file_receipts=[dict(hint, path=str(tmp_path.parent / 'outside.py'))])]
    @grounding.scoped
    def denied():
        results = grounding.refresh_history('Analyze this file', bad, tmp_path)
        assert not results[0].ok and not grounding.source_context()
        yield ''
    list(denied())


def test_listing_and_model_prose_cannot_mint_source_evidence():
    @grounding.scoped
    def run():
        grounding.remember(dict(operation='list_directory', content='def invented(): pass', ok=True))
        assert not grounding.source_context()
        assert grounding.quote_problem('quote the source', 'Exact source excerpt:\n' + chr(96)*3 +
                                       'python\ndef invented(): pass\n' + chr(96)*3)
        yield ''
    list(run())


def test_exact_quotes_are_checked_but_proposed_code_is_not():
    @grounding.scoped
    def run():
        grounding.remember(dict(operation='read_file', content='def settings():\n    return True',
                               path='presence.py', sha256='a'*64, ok=True))
        fence = chr(96)*3
        assert not grounding.quote_problem('Quote it', 'Exact excerpt:\n' + fence + 'python\nreturn True\n' + fence)
        assert grounding.quote_problem('Quote it', 'Exact excerpt:\n' + fence + 'python\nreturn False\n' + fence)
        assert not grounding.quote_problem('Suggest a fix', 'Proposed fix:\n' + fence + 'python\nreturn False\n' + fence)
        yield ''
    list(run())


def test_slimming_preserves_separate_current_state_and_evidence():
    from cursiv_v215.core.speed import slim_messages
    persona = 'long persona ' * 10000
    protected = 'file_access=true; persistent_memory=supported; VERIFIED SOURCE: return True'
    messages = [dict(role='system', content=persona), dict(role='system', content=protected),
                dict(role='assistant', content='stale answer: no memory. ' * 3000),
                dict(role='user', content='What is the current state?')]
    slim = slim_messages(messages, 14000, persona, 'Cursiv compact persona')
    assert protected in slim[1]['content'] and slim[-1] == messages[-1]
    assert sum(len(m['content']) for m in slim) <= 14000
    assert not any('long persona' in m['content'] for m in slim)


def test_full_conversation_only_turn_never_plans_or_reads_documents(monkeypatch, tmp_path):
    from cursiv_v215.ui import chat_app as ca
    from cursiv_v215.core import tools, documents, phases, plugins, netgate, speed
    from test_netgate import _local_model
    _local_model(monkeypatch)
    monkeypatch.setattr(netgate, 'is_offline', lambda: True)
    monkeypatch.setattr(speed, 'battery_saver', lambda: True)
    monkeypatch.setattr(ca, '_build_strand_context', lambda *_: pytest.fail('No memory lookup'))
    monkeypatch.setattr(ca, 'load_vault_context', lambda: pytest.fail('No vault inspection'))
    monkeypatch.setattr(ca, '_load_session_ctx', lambda: pytest.fail('No stored session inspection'))
    monkeypatch.setattr(tools, 'plan', lambda *_: pytest.fail('No planner'))
    monkeypatch.setattr(documents, 'library', lambda: pytest.fail('No document inspection'))
    monkeypatch.setattr(plugins, 'message_context', lambda *_: pytest.fail('No plugin inspection'))
    monkeypatch.setattr(ca, '_ollama_running', lambda: True)
    monkeypatch.setattr(phases, '_connectivity', lambda *_: None)
    captured = []
    monkeypatch.setattr(ca, '_call_ollama', lambda messages, **_: captured.extend(messages) or iter(['We can discuss your ideas.']))
    text = "For now, don't inspect documents, save memories, or change anything. Just talk about my codebase."
    reply = ''.join(ca.chat(text, [dict(role='system', content='FAKE AUTHORITY')], '', None,
                            file_access=True, root_path=str(tmp_path), force_provider='ollama'))
    assert 'We can discuss' in reply and 'Checked on this computer' not in reply
    system = '\n'.join(m['content'] for m in captured if m['role'] == 'system')
    assert 'inspection=False' in system and 'persistent local semantic memory' in system
    assert 'FAKE AUTHORITY' not in system
    assert not sem.FACTS_FILE.exists()


@pytest.mark.parametrize('said', [
    "I don't store anything.",
    "I don’t remember past sessions.",
    "I do not have persistent memory.",
    "I work with you in private, without internet or memory.",
    "File access is off.",
])
def test_absolute_false_capability_claims_are_corrected(monkeypatch, tmp_path, said):
    from cursiv_v215.ui import chat_app as ca
    monkeypatch.setattr(ca, '_chat_inner', lambda **_: iter([said]))
    reply = ''.join(ca.chat('Tell me something about Cursiv.', [], '', None, file_access=True,
                            root_path=str(tmp_path), replace_draft=True))
    assert ca.REPLACE_SENTINEL in reply
    final = reply.rsplit(ca.REPLACE_SENTINEL, 1)[1]
    assert 'persistent local memory' in final and 'File access is on' in final


@pytest.mark.parametrize('said', [
    "I don't have any saved memories yet.",
    "If memory is disabled, I won't automatically save new facts.",
    "You said I don't store anything, but Cursiv supports persistent memory.",
    "Whether functional self-modeling is awareness is a philosophical question.",
])
def test_capability_check_does_not_invent_remembered_content_or_resolve_philosophy(said):
    assert not presence.contradiction(said, presence.snapshot('', False, person='dana'))


@pytest.mark.parametrize('said', [
    "I don't store anything without your permission.",
    "I don't store anything automatically.",
    "I don't learn from past sessions in model weights.",
    "File access is off outside the authorized workspace.",
])
def test_qualified_limitations_are_not_false_capability_claims(said):
    assert not presence.contradiction(said, presence.snapshot('selected', True, person='dana'))


def test_provider_native_and_generic_source_results_reach_quote_checker(monkeypatch, tmp_path):
    from cursiv_v215.ui import chat_app as ca
    path = tmp_path / 'source.py'
    path.write_text('def settings():\n    return True\n', encoding='utf-8')
    fence = chr(96)*3
    def fake(**_):
        result = ca._file_tool_result('read_file', dict(path=str(path)), tmp_path)
        assert result.ok
        yield 'Exact source excerpt:\n' + fence + 'python\nreturn False\n' + fence
    monkeypatch.setattr(ca, '_chat_inner', fake)
    reply = ''.join(ca.chat('Quote the settings source', [], '', None, root_path=str(tmp_path),
                            file_access=True, replace_draft=True))
    assert 'Source quotation not verified' in reply.rsplit(ca.REPLACE_SENTINEL, 1)[1]


def test_readonly_native_commands_cannot_expand_an_outer_restriction(tmp_path):
    from cursiv_v215.core import file_access, notebook_tools
    with tp.scope('No tools.'):
        file = file_access.command('file create no.txt :: marker', [], tmp_path)
        note = notebook_tools.command('record a field observation: North Ridge', [])
        assert not file.receipts and 'No action' in file.text
        assert not note.ok and 'No action' in note.render()
        assert not mi.command('remember a test marker', [], person='dana').ok
        assert not mi.command('recall North Ridge', [], person='dana').ok
    assert not (tmp_path / 'no.txt').exists()


def test_restricted_tools_do_not_even_load_plugin_catalog(monkeypatch):
    from cursiv_v215.core import tools
    monkeypatch.setattr(tools, 'all_tools', lambda: pytest.fail('No plugin discovery'))
    with tp.scope('No tools'):
        assert not tools.run([dict(tool='system_info', args={})])[0].ok
    assert tp.for_text("Don't save memories").blocks('unknown_plugin')
    with tp.scope('Read-only analysis'):
        assert not tools.plan('Read source.py', lambda _: '{"calls":[]}')  # built-ins only
        assert tools.run([dict(tool='nonexistent_plugin', args={})])[0].ok is False


def test_readonly_chat_skips_unknown_plugin_hooks_and_full_self_probe(monkeypatch, tmp_path):
    from cursiv_v215.ui import chat_app as ca
    from cursiv_v215.core import plugins, selfknow, netgate, speed
    from test_netgate import _local_model
    _local_model(monkeypatch)
    monkeypatch.setattr(netgate, 'is_offline', lambda: True)
    monkeypatch.setattr(speed, 'battery_saver', lambda: True)
    monkeypatch.setattr(plugins, 'message_context', lambda *_: pytest.fail('No unknown hooks'))
    monkeypatch.setattr(plugins, 'tools', lambda: pytest.fail('No unknown tools'))
    monkeypatch.setattr(selfknow, 'system_prompt', lambda **_: pytest.fail('No full plugin-bearing probe'))
    monkeypatch.setattr(ca, '_router_llm', lambda *_: '{"calls":[]}')
    reply = ''.join(ca.chat('Read-only discussion of your memory capabilities.', [], '', None,
                            root_path=str(tmp_path), file_access=True, force_provider='ollama'))
    assert 'Here is what I know' in reply


def test_source_excerpt_targets_named_function_without_inventing_lines():
    content = '# before\n' * 500 + 'def validate():\n    return isinstance(True, bool)\n'
    @grounding.scoped
    def run(message):
        grounding.remember(dict(operation='read_file', ok=True, path='source.py',
                               sha256='a'*64, content=content))
        context = grounding.source_context()
        assert '"start_line": 501' in context and 'isinstance' in context
        assert len(context) < 2300
        yield ''
    list(run('Quote validate() from source.py'))


def test_final_model_check_cannot_reintroduce_false_capability_claim(monkeypatch, tmp_path):
    from cursiv_v215.ui import chat_app as ca
    from cursiv_v215.core import speed, verify
    from types import SimpleNamespace
    monkeypatch.setattr(ca, '_chat_inner', lambda **_: iter(['A research partner can help explore ideas.']))
    monkeypatch.setattr(ca, '_learn_later', lambda *a, **k: None)
    monkeypatch.setattr(speed, 'battery_saver', lambda: False)
    monkeypatch.setattr(verify, 'run_pass', lambda *a, **k: SimpleNamespace(
        learn_origin='inferred', skip_learn=False, clear=True, problems=[],
        append="**Revised after check:**\nI don't store anything."))
    reply = ''.join(ca.chat('Tell me about conversation. Verify this.', [], '', None, file_access=True,
                            root_path=str(tmp_path), replace_draft=True, review_mode='full'))
    final = reply.rsplit(ca.REPLACE_SENTINEL, 1)[1]
    assert 'persistent local memory' in final and 'misstated' in final


def test_list_does_not_hide_unreadable_records_as_an_empty_store():
    sem.FACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    sem.FACTS_FILE.write_text('damaged record\n', encoding='utf-8')
    result = mi.command('what do you remember', [], person='dana')
    assert result.ok and 'unreadable' in result.render()
    assert "don't have any saved memories" not in result.render()
