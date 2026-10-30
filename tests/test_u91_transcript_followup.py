"""U91 live transcript regressions; synthetic data, fake models and offscreen Qt."""
import pytest

from cursiv_engine.core import philosophy_policy, presence, selfknow, style
from test_background_review import pipeline
from test_chat_rendering import panel
from test_documents import library
from test_live_test_followup import final_reply


@pytest.mark.parametrize('offline', [True, False])
@pytest.mark.parametrize('question', [
    'What is your version, and are you offline right now?',
    'What is your version and are you offline right now?',
    "What's your current version, and are you offline?",
])
def test_combined_state_with_punctuation(pipeline, monkeypatch, question, offline):
    from cursiv_engine.core import netgate
    monkeypatch.setattr(netgate, 'is_offline', lambda: offline)
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model state'))
    out = final_reply(pipeline, question)
    assert selfknow.VERSION in out
    assert ('Offline mode is on' if offline else 'Offline mode is off') in out
    assert 'application state' in out


@pytest.mark.parametrize('stream', [True, False])
@pytest.mark.parametrize('body', [
    'File access is off. Choose workspace <folder>, then files on. No file was accessed.',
    'Phone capture: https://cursiv.us/notebook — field log import <file>.\n\nA first visit needs a connection.',
    'Use <path-to-file>.cursivsync, then verify the imported entries.',
])
def test_literal_placeholders_survive_streaming_and_final_render(panel, body, stream):
    panel._on_chunk(body + '\n\nEnd of instructions.')
    if stream:
        panel._flush_reply_chunks()
        assert ' '.join(body.split()) in ' '.join(panel._transcript.toPlainText().split())
    panel._on_done()
    shown = panel._transcript.toPlainText()
    assert ' '.join(body.split()) in ' '.join(shown.split()) and 'End of instructions.' in shown


def test_no_html_keeps_markdown_links_tables_and_code(panel):
    panel._on_chunk('**Instructions**: <file>\n\n[Notebook](https://cursiv.us/notebook)\n\n'
                    '| A | B |\n|---|---|\n| 1 | 2 |\n\n```html\n<b>literal</b>\n```')
    panel._on_done()
    html = panel._transcript.toHtml()
    assert '<file>' in panel._transcript.toPlainText()
    assert '<b>literal</b>' in panel._transcript.toPlainText()
    assert '<table' in html and '<pre' in html and 'href="https://cursiv.us/notebook"' in html


@pytest.mark.parametrize('provider', ['ollama', 'openai'])
def test_explicit_document_miss_stops_before_model(library, pipeline, tmp_path, monkeypatch, provider):
    path = tmp_path / 'test-protocol.txt'
    path.write_text('Test protocol: Take three readings at each site. Record water temperature in Celsius.',
                    encoding='utf-8')
    library.add(path)
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **k: pytest.fail('No model after document miss'))
    monkeypatch.setattr(pipeline, '_call_openai_direct', lambda *a, **k: pytest.fail('No cloud after document miss'))
    out = final_reply(pipeline, 'According to that protocol, which brand of thermometer is required?',
        [dict(role='user', content='According to the test protocol, how many readings should I take?'),
         dict(role='assistant', content='Three readings.')], force_provider=provider)
    assert 'No matching passage' in out and 'test-protocol.txt' in out
    assert 'no AI model' in out and 'model knowledge' not in out
    assert "don't have access" not in out and 'consult the full protocol' not in out


PAIRED = ('Now give the strongest argument for moral realism, then the strongest objection. '
          'Present them as arguments, not established facts.')


@pytest.mark.parametrize('prefix', ['', 'Just talk. No tools. '])
def test_paired_philosophy_arguments_are_bounded_and_balanced(pipeline, monkeypatch, prefix):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No definitive model verdict'))
    out = final_reply(pipeline, prefix + PAIRED)
    assert philosophy_policy.INTRO in out and 'Argument for moral realism' in out and 'Objection' in out
    assert 'not established conclusions' in out and 'does not by itself disprove' in out
    assert 'no AI model' in out


COMPARISON = ('I want a research partner who will challenge my assumptions. I think two assistants '
              'with identical code must behave identically, even if they have different saved memories. '
              'What am I overlooking? Keep it under 150 words.')


def test_memory_comparison_uses_known_capabilities_not_invented_mechanisms(pipeline, monkeypatch):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No invented memory decay'))
    out = final_reply(pipeline, COMPARISON)
    assert 'different inputs' in out and 'retrieved context' in out and 'not retrain' in out
    assert 'memory decay' not in out and 'no AI model' in out
    assert len(out.split()) < 150


@pytest.mark.parametrize('question', [
    'If I erased your memories, would you still be the same Cursiv?',
    'Write a story about two assistants with identical code and different saved memories.',
    'Create notes.txt with the text: two assistants with identical code and different saved memories.',
    'Explain memory decay in humans.',
])
def test_memory_comparison_does_not_capture_other_requests(question):
    assert presence.memory_comparison_answer(question) is None


@pytest.mark.parametrize('provider,method', [
    ('ollama', '_call_ollama'), ('openai', '_call_openai_direct'),
    ('grok', '_call_xai_stream'), ('claude', '_call_claude_direct'),
])
def test_style_rule_is_current_and_survives_compaction(pipeline, monkeypatch, provider, method):
    from cursiv_engine.memory import semantic
    from cursiv_engine.core import netgate
    seen = []
    monkeypatch.setattr(netgate, 'is_offline', lambda: False)
    monkeypatch.setattr(pipeline, '_build_strand_context', lambda *a, **k: '')
    monkeypatch.setattr(pipeline, method, lambda messages, *a, **k: seen.extend(messages) or iter(['A short answer.']))
    from cursiv_engine.chat import provider_adapters, provider_manager, provider_settings
    def normalized_model(request, result, credential):
        seen.extend(request.messages)
        result.text='A short answer.'
        result.responding_provider=request.provider
        result.finish_reason='stop'
        yield result.text
    monkeypatch.setattr(provider_adapters,'stream',normalized_model)
    monkeypatch.setattr(provider_settings,'key',lambda p:'synthetic-credential')
    person = semantic.current_person()
    style.add_rule(person, 'Answer in about 60 words, with no examples.', 'manual')
    options = dict(force_provider=provider, openai_key='fixture', anthropic_key='fixture')
    # The helper supplies an empty xAI key; use the public chat call for that provider.
    def ask():
        with provider_manager.turn_options(research_authorized=True):
            return ''.join(pipeline.chat('Explain the difference between an observation and an inference.',
                                        [], 'fixture', None, **options))
    ask()
    blocks = [m for m in seen if m.get('role') == 'system' and m.get('content', '').startswith('## Current answer style')]
    assert len(blocks) == 1 and '60 words' in blocks[0]['content'] and 'overrides these preferences' in blocks[0]['content']
    slim = pipeline._slim(seen, 4000)
    assert sum(m == blocks[0] for m in slim) == 1
    assert sum(m == blocks[0] for m in pipeline._slim(slim, 4000)) == 1
    seen.clear()
    style.clear(person)
    ask()
    assert not any(m.get('content', '').startswith('## Current answer style') for m in seen)
    assert not any('Current tone' in m.get('content', '') for m in seen)


def test_long_style_rules_cannot_exhaust_compact_budget(pipeline):
    from cursiv_engine.memory import semantic
    person = semantic.current_person()
    style.add_rule(person, 'Answer in about 60 words.', 'manual')
    for i in range(14):
        style.add_rule(person, f'Presentation rule {i}: ' + 'plain words ' * 15)
    block = style.prompt_addendum(person, 'Explain observation versus inference.')
    messages = [dict(role='system', content='Persona ' * 2000),
                dict(role='system', content=block), dict(role='user', content='Explain observation versus inference.')]
    slim = pipeline._slim(messages, 4000)
    assert sum(len(m['content']) for m in slim) <= 4000
    assert any('60 words' in m['content'] for m in slim)


def test_document_miss_does_not_block_attached_material(library, pipeline, tmp_path, monkeypatch):
    imported = tmp_path / 'protocol.txt'
    imported.write_text('Take three readings. Record temperature in Celsius.', encoding='utf-8')
    library.add(imported)
    attached = tmp_path / 'attachment.txt'
    attached.write_text('The attached protocol specifies a fictional Birch thermometer.', encoding='utf-8')
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **k: iter(['Attached-material discussion.']))
    out = final_reply(pipeline, dict(text='According to that protocol, which brand of thermometer is required?',
                                   files=[str(attached)]), force_provider='ollama')
    assert 'Attached-material discussion.' in out


@pytest.mark.parametrize('question', [
    'Explain this in detail with examples.', 'Write a Python function and a three-row table.',
    'Give all the steps and warnings for this task.', 'Write a 200-word explanation.',
])
def test_explicit_detail_overrides_brief_preference(question):
    from cursiv_engine.memory import semantic
    person = semantic.current_person()
    style.add_rule(person, 'Keep answers short', 'manual')
    assert 'The current request overrides these preferences.' in style.prompt_addendum(person, question)


def test_talk_only_does_not_read_style_preferences(pipeline, monkeypatch):
    monkeypatch.setattr(style, 'load', lambda *a, **k: pytest.fail('No saved-style lookup'))
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **k: iter(['An observation records; an inference interprets.']))
    out = final_reply(pipeline, 'Just talk. No tools. Explain observation versus inference.', force_provider='ollama')
    assert 'An observation records' in out
