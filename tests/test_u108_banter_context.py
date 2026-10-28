"""Explicit brief banter must not load unrelated private or operational context."""
import pytest
from cursiv_engine.core import conversation_kind
from test_background_review import pipeline
from test_live_test_followup import final_reply

QUESTION='My to-do list just filed a complaint against me. One short reply, no advice.'


def test_explicit_brief_banter_excludes_personal_context():
    assert not conversation_kind.personal_context_allowed(QUESTION)


@pytest.mark.parametrize('service',['load_vault_context','_load_session_ctx','_build_strand_context'])
def test_brief_banter_does_not_read_unrelated_context(pipeline,monkeypatch,service):
    monkeypatch.setattr(pipeline,service,lambda *a,**k:pytest.fail('No unrelated context for explicit brief banter'))
    assert final_reply(pipeline,QUESTION,[],review_mode='off')


def test_brief_banter_does_not_get_workspace_coding_instructions(pipeline,monkeypatch,tmp_path):
    sent=[]
    monkeypatch.setattr(pipeline,'_call_ollama',lambda messages,**k:sent.extend(messages) or iter(['The list has retained a very tiny lawyer.']))
    final_reply(pipeline,QUESTION,[],file_access=True,root_path=str(tmp_path),review_mode='off')
    assert not any('CODING PROTOCOL' in str(m.get('content','')) for m in sent)


@pytest.mark.parametrize('question',[
    'Keep it light, but I have chest pain.',
    'One short reply, no advice: convert 5 mg to grams.',
    'That was a joke. Explain the source code.',
    'No pep talk: search my notebook for sample ID AB-1.',
    'Summarize my document and keep it light.',
    'Use my saved memories, no pep talk.',
])
def test_safety_calculations_source_and_retrieval_keep_normal_routes(question):
    assert not conversation_kind.light_banter(question)


def test_banter_does_not_retrieve_documents_or_plugins(pipeline,monkeypatch):
    from cursiv_engine.core import documents,plugins
    from cursiv_engine.memory import projects
    def forbidden(*a,**k):pytest.fail('No unrelated retrieval for explicit banter')
    monkeypatch.setattr(documents,'library',forbidden)
    monkeypatch.setattr(plugins,'message_context',forbidden)
    monkeypatch.setattr(projects,'context',forbidden)
    assert final_reply(pipeline,QUESTION,[],review_mode='off')
