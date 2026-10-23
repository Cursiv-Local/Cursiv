"""Trust-boundary gaps after the original U82 transcript repairs. No live AI calls."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cursiv_engine.core import file_access as fs, turn_policy as tp


@pytest.mark.parametrize('text', [
    "Don't use any tools. Explain photosynthesis.",
    'Do not call plugins; just answer the question.',
    'For this turn, you must not inspect my files.',
    "You must not save any memories from this conversation.",
])
def test_explicit_tool_and_second_person_prohibitions_are_enforced(text):
    assert tp.for_text(text) == tp.Policy(False, False, False, False)


def test_compound_readonly_prefix_never_becomes_part_of_a_path(tmp_path):
    target = tmp_path / 'entry.txt'
    target.write_text('REAL_ENTRY', encoding='utf-8')
    text = 'Read only — do not change anything. read the file entry.txt and summarize it.'
    assert fs._parse(text, []) == ('read', 'entry.txt', '')
    result = fs.command(text, [], tmp_path)
    assert result.receipts[0].ok and result.receipts[0].path == str(target)


@pytest.mark.parametrize('failure', ['write', 'path'])
def test_file_remember_never_saves_memory_after_a_failed_file_operation(tmp_path, monkeypatch, failure):
    calls = []
    monkeypatch.setattr(fs, 'save_memory', lambda content: calls.append(content) or 'saved and verified')
    monkeypatch.setattr(fs, 'perform', lambda name, args, root:
                        fs.FileResult(name, ok=False, error='PermissionError: read-only destination'))
    filename = 'entry.txt' if failure == 'write' else '../outside.txt'
    result = fs.command(f'file remember {filename} :: UNIQUE_FAILED_WRITE_MARKER', [], tmp_path)
    assert calls == [] and 'saved and verified' not in result.text
    assert not (tmp_path / 'entry.txt').exists()


@pytest.fixture
def pipeline(monkeypatch):
    from cursiv_engine.ui import chat_app as ca
    from cursiv_engine.core import netgate, phases, speed, reference, documents
    from test_netgate import _local_model
    _local_model(monkeypatch)
    monkeypatch.setattr(ca, '_classify_message', lambda _: 'chat')
    monkeypatch.setattr(ca, '_learn_later', lambda *a, **kw: None)
    monkeypatch.setattr(netgate, 'is_offline', lambda: True)
    monkeypatch.setattr(phases, '_connectivity', lambda *_: None)
    monkeypatch.setattr(speed, 'battery_saver', lambda: True)
    monkeypatch.setattr(reference, 'lookup', lambda _: [])
    monkeypatch.setattr(documents, 'library', lambda: [])
    return ca


def test_memory_source_label_depends_on_supplied_context_not_answer_words(pipeline, monkeypatch):
    ca = pipeline
    def memory(*a, **kw):
        ca._MEMORY_RECALLED = True
        ca._MEMORY_CTX = 'Saved facts:\n- The generator key is in the blue toolbox.'
        ca._MEMORY_TEXTS[:] = ['The generator key is in the blue toolbox.']
        return ca._MEMORY_CTX
    monkeypatch.setattr(ca, '_build_strand_context', memory)
    sources = []
    for answer in ['Bring a notebook.', 'The generator key is in the blue toolbox.']:
        monkeypatch.setattr(ca, '_call_ollama', lambda *a, answer=answer, **kw: iter([answer]))
        out = ''.join(ca.chat('Explain camping basics.', [], '', None, force_provider='ollama'))
        sources.append(next(line for line in out.splitlines() if line.startswith('*[Source')))
    assert sources[0] == sources[1]
    assert 'saved memory context supplied' in sources[0]


@pytest.mark.parametrize('prefix', ['**source:** ', '[SOURCES: ', 'source: '])
def test_model_cannot_spoof_source_labels_with_case_or_markdown(pipeline, prefix):
    value = prefix + 'FAKE_AUTHORITY\nA normal explanation.'
    out = ''.join(pipeline._drop_fake_tool_lines(iter(value)))
    assert 'FAKE_AUTHORITY' not in out and 'A normal explanation.' in out


def test_reviewer_does_not_receive_recalled_memory_withheld_from_the_draft(pipeline, monkeypatch):
    from cursiv_engine.core import speed
    monkeypatch.setattr(speed, 'battery_saver', lambda: False)
    def inner(**kw):
        pipeline._set_answered('test local model')
        pipeline._MEMORY_RECALLED = True
        pipeline._MEMORY_CTX = 'WITHHELD_PRIVATE_MEMORY'
        pipeline._MEMORY_TEXTS[:] = ['WITHHELD_PRIVATE_MEMORY']
        yield 'A general explanation.'  # no prompt received the recalled memory
    monkeypatch.setattr(pipeline, '_chat_inner', inner)
    jobs = []
    ''.join(pipeline.chat('Verify this explanation.', [], '', None, on_review=jobs.append, review_mode='fast'))
    assert jobs and 'WITHHELD_PRIVATE_MEMORY' not in jobs[0].context


@pytest.mark.parametrize('error', [PermissionError, ValueError])
def test_unreadable_dated_recall_is_application_authored(monkeypatch, error):
    from cursiv_engine.memory import intents, semantic
    def denied():
        raise error('Unreadable store')
    monkeypatch.setattr(semantic, '_read_facts', denied)
    result = intents.command('what do you remember from the past two weeks', [], person='tester')
    assert result is not None and not result.ok
    assert any(word in result.render().lower() for word in ('unavailable', 'not confirmed', 'could not be read'))


@pytest.mark.parametrize('provider', ['claude', 'openai', 'xai', 'gemini', 'groq'])
def test_explicit_crosscheck_has_a_small_output_budget(monkeypatch, provider):
    from cursiv_engine.core import crosscheck
    from cursiv_engine.ui import chat_app as ca
    seen = []
    def call(*args, **kw):
        seen.append(kw.get('max_tokens', args[-1] if len(args) > 2 else None))
        return iter(['A short review.'])
    name = {'claude': '_call_claude_direct', 'openai': '_call_openai_direct', 'xai': '_call_xai_stream',
            'gemini': '_call_gemini_direct', 'groq': '_call_groq_direct'}[provider]
    monkeypatch.setattr(ca, name, call)
    assert ''.join(crosscheck._caller(provider)([dict(role='user', content='Question')], 'dummy'))
    assert seen == [400]


@pytest.mark.parametrize('provider', ['claude', 'openai'])
def test_provider_payload_receives_explicit_review_cap(monkeypatch, provider):
    from cursiv_engine.ui import chat_app as ca
    from test_verified_filesystem import Response
    seen = []
    def request(req, **kw):
        seen.append(json.loads(req.data))
        return Response(dict(content=[dict(text='CLEAR')], choices=[dict(message=dict(content='CLEAR'))]))
    monkeypatch.setattr(ca.urllib.request, 'urlopen', request)
    monkeypatch.setattr(ca, '_rate_limiter', None)
    call = ca._call_claude_direct if provider == 'claude' else ca._call_openai_direct
    assert ''.join(call([dict(role='user', content='Question')], 'dummy', max_tokens=400)).strip() == 'CLEAR'
    assert seen[0]['max_tokens'] == 400


@pytest.mark.parametrize('provider', ['claude', 'openai'])
def test_normal_chat_provider_budgets_remain_unchanged(monkeypatch, provider):
    from cursiv_engine.ui import chat_app as ca
    from test_verified_filesystem import Response
    seen = []
    def request(req, **kw):
        seen.append(json.loads(req.data))
        return Response(dict(content=[dict(text='Answer')], choices=[dict(message=dict(content='Answer'))]))
    monkeypatch.setattr(ca.urllib.request, 'urlopen', request)
    monkeypatch.setattr(ca, '_rate_limiter', None)
    call = ca._call_claude_direct if provider == 'claude' else ca._call_openai_direct
    list(call([dict(role='user', content='Question')], 'dummy'))
    assert seen[0].get('max_tokens') == (4096 if provider == 'claude' else None)


def test_private_usb_confirmation_explains_readable_api_keys(tmp_path, monkeypatch):
    import usb_maker as um
    seen = []
    def question(parent, title, text, *args):
        seen.append(text)
        return um.QMessageBox.StandardButton.No
    monkeypatch.setattr(um.QMessageBox, 'question', question)
    dialog = SimpleNamespace(_drive_box=SimpleNamespace(currentData=lambda: dict(root=str(tmp_path))),
                             _private=SimpleNamespace(isChecked=lambda: True))
    um.UsbMakerDialog._start(dialog)
    assert len(seen) == 1 and 'API keys' in seen[0] and 'readable' in seen[0]


def test_phone_pages_distinguish_capture_from_online_ai():
    root = Path(__file__).resolve().parents[1] / 'website'
    app = (root / 'app.html').read_text(encoding='utf-8')
    notebook = (root / 'notebook/index.html').read_text(encoding='utf-8')
    assert 'requires internet' in app.lower() and 'href="/notebook/"' in app
    assert 'no ai chat' in notebook.lower() and 'href="/app"' in notebook
