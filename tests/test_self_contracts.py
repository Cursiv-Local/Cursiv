"""Critical app rules use inspected source contracts, not model interpretation."""
import pytest
from cursiv_engine.core import self_inspection, self_contracts, self_index
from test_background_review import pipeline
from test_live_test_followup import final_reply


@pytest.mark.parametrize('question,expected',[
    ('Where does your code enforce confirmation?','stops unless you choose Save'),
    ('Do you replace my original notebook reading when I correct it?','original stays in the stored log'),
    ('What happens if your local model fails?','before the `local_tried` return'),
])
def test_critical_rule_explanations_are_native_and_do_not_execute(pipeline,monkeypatch,question,expected):
    from cursiv_engine.core import fieldlog, file_access
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:pytest.fail('Critical rules do not depend on model prose'))
    monkeypatch.setattr(fieldlog,'entries',lambda *a,**k:pytest.fail('Do not open notebook data'))
    monkeypatch.setattr(file_access,'perform',lambda *a,**k:pytest.fail('No workspace inspection'))
    out=final_reply(pipeline,question,[],review_mode='off')
    assert expected in out and 'Written by Cursiv, no AI model' in out


@pytest.mark.parametrize('question,original,replacement',[
    ('Where does your code enforce confirmation?',"what != \"save\" or not proposal.ok","what != \"save\""),
    ('Do you replace my original notebook reading when I correct it?',
     'private_store.write_text(log_file(), text + line)','private_store.write_text(log_file(), line)'),
    ('What happens if your local model fails?',
     'if local_tried:     # it already had its turn first and didn\'t answer','if False:     # changed implementation'),
])
def test_changed_source_witness_does_not_fall_back_to_a_model(monkeypatch,question,original,replacement):
    token=self_inspection._active.set(None)
    try:
        packet=self_inspection.prepare(question)
        assert packet and not packet.error
        read=self_index.text
        changed=[]
        def text(*args):
            body=read(*args)
            if original in body:
                changed.append(True)
                body=body.replace(original,replacement)
            return body
        monkeypatch.setattr(self_index,'text',text)
        out=self_contracts.answer(packet,question)
        assert changed and 'unavailable' in out and 'model guess' in out
    finally:
        self_inspection._active.reset(token)


def test_packaged_selftest_exercises_own_source_without_a_model(monkeypatch):
    import selftest
    from cursiv_engine.core import fieldlog
    monkeypatch.setattr(fieldlog,'entries',lambda:pytest.fail('No private notebook access'))
    result=dict(selftest._checks())['own source']()
    assert 'critical-rule witnesses pass' in result
