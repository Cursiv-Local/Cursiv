"""Qt accepts owned workflow/ordinary outputs only in their original turn."""
import threading

from test_chat_feedback import panel


def test_queued_text_and_history_cannot_arrive_in_a_new_conversation(panel):
    panel._begin_turn('Old question')
    target=panel._run_target()
    panel.new_conversation()
    panel._on_run_event(target,dict(kind='chunk',text='old private result'))
    panel._on_run_event(target,dict(kind='done',history=[('assistant','old private result')]))
    assert 'old private result' not in panel._transcript.toPlainText()
    assert not panel._history and not panel._streaming and panel._send_btn.isEnabled()


def test_stale_worker_cannot_start_after_a_new_turn(panel,monkeypatch):
    import chat_commands
    panel._begin_turn('Old question')
    old=panel._run_target()
    panel.new_conversation()
    panel._begin_turn('New question')
    monkeypatch.setattr(chat_commands,'handle_command',lambda *a,**k:(_ for _ in ()).throw(AssertionError('stale dispatch')))
    panel._run_turn('Old question',[],turn_target=old)
    assert panel._streaming and not panel._reply_text


def test_workspace_change_rejects_queued_result_and_releases_controls(panel):
    panel._begin_turn('Old workspace')
    target=panel._run_target()
    panel._cfg['workspace']='different synthetic workspace'
    panel._on_run_event(target,dict(kind='chunk',text='private old workspace content'))
    assert 'private old workspace content' not in panel._transcript.toPlainText()
    assert not panel._streaming and panel._send_btn.isEnabled()


def test_changed_workspace_authorization_rejects_run_and_releases_controls(panel,monkeypatch):
    from types import SimpleNamespace
    from cursiv_engine.agents import workflow
    panel._begin_turn('Old workspace authorization')
    target=panel._run_target()
    run=SimpleNamespace(owner=workflow.identity())
    monkeypatch.setattr(workflow,'identity',lambda: ('different authorized workspace',))
    panel._on_run_event(target,dict(kind='done',history=[('assistant','old workspace answer')],run=run))
    assert not panel._history and 'old workspace answer' not in panel._transcript.toPlainText()
    assert not panel._streaming and panel._send_btn.isEnabled()


def test_current_owned_result_is_displayed_and_saved_to_this_history(panel):
    panel._begin_turn('Current question')
    target=panel._run_target()
    panel._on_run_event(target,dict(kind='chunk',text='Current answer.'))
    panel._on_run_event(target,dict(kind='done',history=[('user','Current question'),('assistant','Current answer.')]))
    assert panel._history[-1]['content']=='Current answer.'
    assert 'Current answer.' in panel._transcript.toPlainText()


def test_legacy_command_stream_uses_owned_publication_and_retains_history(panel):
    import chat_commands
    panel._begin_turn('translate hello')
    completed=[]
    result=chat_commands.StreamResult('Translation',iter(['Bonjour']),lambda text:completed.append(text))
    panel._deliver_result(result,[],'translate hello')
    assert completed==['Bonjour'] and panel._history[-1]['content']=='Bonjour'


def test_plain_agent_list_result_is_guarded_at_qt_acceptance(panel):
    import chat_commands
    panel._begin_turn('agents')
    target=panel._run_target()
    panel.new_conversation()
    panel._deliver_result(chat_commands.TextResult('Private old profile names'),[],'agents',turn_target=target)
    assert 'Private old profile names' not in panel._transcript.toPlainText() and not panel._history


def test_research_answer_markdown_footer_is_rendered(panel):
    from types import SimpleNamespace
    from cursiv_engine.agents.workflow import identity
    panel._begin_turn('Research question')
    target=panel._run_target()
    run=SimpleNamespace(owner=identity())
    panel._on_run_event(target,dict(kind='chunk',text='An answer.\n\n*[Profiles completed: @field; code only]*',run=run))
    panel._on_run_event(target,dict(kind='done',history=None,run=run))
    assert '*[Profiles' not in panel._transcript.toPlainText()
    assert 'Profiles completed:' in panel._transcript.toPlainText()


def _note_worker(panel,monkeypatch):
    from types import SimpleNamespace
    import chat_actions,conversations
    from cursiv_engine.ui import chat_app
    panel._conv_id='synthetic-owned-note'
    panel._history=[dict(role='user',content='Plan a creek survey.'),dict(role='assistant',content='A draft.')]
    workers=[]
    monkeypatch.setattr(chat_actions.threading,'Thread',lambda target,**kw:SimpleNamespace(start=lambda:workers.append(target)))
    monkeypatch.setattr(conversations,'list_all',lambda:[])
    monkeypatch.setattr(chat_app,'_local_model_ready',lambda:False)
    panel._update_session_note()
    assert len(workers)==1
    return workers[0]


def test_delayed_session_note_never_writes_into_a_later_storage_context(panel,monkeypatch,tmp_path):
    from cursiv_engine.memory import session_notes
    original=session_notes.DIR
    worker=_note_worker(panel,monkeypatch)
    other=tmp_path/'different-person-store'
    monkeypatch.setattr(session_notes,'DIR',other)
    worker()
    assert not original.exists() and not other.exists()


def test_session_note_same_owner_still_persists_to_its_captured_destination(panel,monkeypatch):
    from cursiv_engine.memory import session_notes
    worker=_note_worker(panel,monkeypatch)
    worker()
    assert 'Conversation' in session_notes.load('synthetic-owned-note')


def test_delayed_session_note_stops_before_model_after_person_change(panel,monkeypatch):
    from cursiv_engine.memory import semantic,session_notes
    worker=_note_worker(panel,monkeypatch)
    semantic.set_person('different-person')
    worker()
    assert not session_notes.DIR.exists()


def test_research_completion_cannot_launch_unbudgeted_note_summary(panel,monkeypatch):
    from types import SimpleNamespace
    from cursiv_engine.agents.workflow import identity
    from cursiv_engine.ui import chat_app
    from cursiv_engine.memory import session_notes
    panel._begin_turn('Research request')
    panel._on_run_event(panel._run_target(),dict(kind='done',run=SimpleNamespace(owner=identity()),
                        history=[('user','Research request'),('assistant','A code-only answer.')]))
    worker=_note_worker(panel,monkeypatch)
    monkeypatch.setattr(chat_app,'_local_model_ready',lambda:True)
    calls=[]
    monkeypatch.setattr(chat_app,'_local_llm',lambda *a:calls.append(a) or '')
    worker()
    assert session_notes.load('synthetic-owned-note') and not calls


def test_cancelled_session_note_worker_cannot_persist(panel,monkeypatch):
    from cursiv_engine.memory import session_notes
    panel._begin_turn('Old request')
    worker=_note_worker(panel,monkeypatch)
    panel._cancel_event.set()
    worker()
    assert not session_notes.DIR.exists()
