"""Frozen automatic self-inspection probes, before implementation; synthetic/public code only."""
from pathlib import Path
import pytest
from cursiv_engine.core import self_source, file_access
from test_background_review import pipeline
from test_live_test_followup import final_reply

CASES = [
    ('How do you process my messages, from the chat box to your reply?', [], 'chat/completion.py'),
    ('And where does the model actually get called?', ['How do you process my messages, from the chat box to your reply?'], 'chat/local_provider.py'),
    ('How does your notebook find a sample I saved?', [], 'core/field_recall.py'),
    ('Where exactly is confirmation enforced?', ['How does your notebook save observations?'], 'core/notebook_tools.py'),
    ('How do you keep files inside the folder I authorized?', [], 'core/file_access.py'),
    ('What happens if your local model fails?', [], 'chat/routing.py'),
]


@pytest.fixture
def own_source(monkeypatch):
    """Allow only named public files; never let baseline search enumerate owner documents."""
    root = Path(__file__).resolve().parents[1]
    allowed = ['docs/CODE-MAP.md', 'ARCHITECTURE.md', 'cursiv_engine/core/selfknow.py',
               'cursiv_engine/core/notebook_tools.py', 'cursiv_engine/core/field_recall.py',
               'cursiv_engine/core/fieldlog.py', 'cursiv_engine/core/file_access.py',
               'cursiv_engine/ui/chat_app.py', 'cursiv_engine/chat/completion.py',
               'cursiv_engine/chat/conversation.py', 'cursiv_engine/chat/local_provider.py',
               'cursiv_engine/chat/routing.py', 'launcher/chat_panel.py']
    monkeypatch.setattr(self_source, 'files', lambda: allowed)
    return root


@pytest.mark.parametrize('question,earlier,expected', CASES)
def test_normal_questions_automatically_receive_owned_code(pipeline, monkeypatch, own_source, question, earlier, expected):
    sent = []
    def answer(messages, **kwargs):
        sent.extend(messages)
        return iter(['The supplied source describes this path.'])
    monkeypatch.setattr(pipeline, '_call_ollama', answer)
    monkeypatch.setattr(file_access, 'perform', lambda *a, **k: pytest.fail('Own code must not use workspace grant'))
    history = [dict(role='user', content=q) for q in earlier]
    out=final_reply(pipeline, question, history, file_access=False, force_provider='ollama', review_mode='off')
    if not sent:
        assert expected in out and 'Written by Cursiv, no AI model' in out
        return  # source-checked native contracts replace model interpretation of critical rules
    systems = '\n'.join(m['content'] for m in sent if m['role'] == 'system')
    assert 'Installed Cursiv source evidence' in systems
    assert expected in systems
    assert 'runtime execution was not observed' in systems


def test_followup_does_not_inherit_another_conversation(pipeline, monkeypatch, own_source):
    sent = []
    monkeypatch.setattr(pipeline, '_call_ollama', lambda messages, **kw: sent.extend(messages) or iter(['Which model path do you mean?']))
    final_reply(pipeline, 'And where does the model actually get called?', [], force_provider='ollama', review_mode='off')
    assert not any('Installed Cursiv source evidence' in m['content'] for m in sent if m['role']=='system')


def test_no_tools_does_not_read_own_source(pipeline, monkeypatch):
    monkeypatch.setattr(self_source, 'read', lambda *a, **k: pytest.fail('No restricted source read'))
    monkeypatch.setattr(self_source, 'search', lambda *a, **k: pytest.fail('No restricted source search'))
    out = final_reply(pipeline, 'No tools. How do you process my messages?', [], review_mode='off')
    assert out


def test_own_inspection_does_not_consult_saved_documents_or_workspace(pipeline,monkeypatch,own_source):
    from cursiv_engine.core import documents, plugins, presence
    def forbidden(*a,**k): pytest.fail('Own implementation questions do not retrieve personal context or tools')
    monkeypatch.setattr(documents,'library',forbidden)
    monkeypatch.setattr(plugins,'message_context',forbidden)
    monkeypatch.setattr(pipeline,'_build_strand_context',forbidden)
    monkeypatch.setattr(file_access,'perform',forbidden)
    monkeypatch.setattr(presence,'snapshot',forbidden)
    out=final_reply(pipeline,CASES[0][0],[],review_mode='off')
    assert out


def test_unavailable_local_model_never_falls_back_to_cloud(pipeline,monkeypatch,own_source):
    from cursiv_engine.core import source_analysis
    monkeypatch.setattr(source_analysis,'native',lambda *a:None)  # deliberately exercise the model guard path
    monkeypatch.setattr(pipeline,'_ollama_running',lambda:False)
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:pytest.fail('No missing-model generation'))
    monkeypatch.setattr(pipeline,'_free_key_llm',lambda *a,**k:pytest.fail('No cloud fallback for own code'))
    out=final_reply(pipeline,CASES[0][0],[],force_provider='openai',review_mode='off')
    assert 'exact provider/model' in out and 'no source was sent' in out and 'No fallback' in out


def test_invented_implementation_reference_is_withdrawn(pipeline,monkeypatch,own_source):
    from cursiv_engine.core import source_analysis
    monkeypatch.setattr(source_analysis,'native',lambda *a:None)  # deliberately exercise the model guard path
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:iter(['It runs cursiv_engine/private/fake.py:99.']))
    out=final_reply(pipeline,CASES[0][0],[],review_mode='off')
    assert out.startswith('Source explanation withheld:')


def test_inline_own_source_review_never_routes_to_cloud(pipeline,monkeypatch,own_source):
    import threading
    from cursiv_engine.chat import review
    from cursiv_engine.core import self_inspection
    monkeypatch.setattr(pipeline,'_router_llm',lambda *a,**k:pytest.fail('No cloud-capable router for own-code review'))
    monkeypatch.setattr(pipeline,'_ollama_running',lambda:False)
    token=self_inspection._active.set(None)
    try:
        packet=self_inspection.prepare(CASES[0][0])
        assert packet and not packet.error
        job=review.prepare(pipeline,CASES[0][0],'These are static source excerpts.',[], 'full',background=False)
        assert job is not None
        assert job.ask([dict(role='system',content='Review the source explanation.')],threading.Event())==''
    finally:
        self_inspection._active.reset(token)


def test_source_reading_is_not_a_physical_measurement(pipeline,monkeypatch,own_source):
    from cursiv_engine.core import science_check
    monkeypatch.setattr(science_check,'overconfidence_note',lambda *a:pytest.fail('Code history is not a physical reading'))
    out=final_reply(pipeline,'How does your implementation preserve original notebook readings?',[],review_mode='off')
    assert out
