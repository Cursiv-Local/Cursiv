"""U109 observed failures frozen before runtime repairs; public/synthetic code only."""
import json
from pathlib import Path
import pytest
from cursiv_engine.core import self_inspection as own, self_source, self_index, source_inspection, turn_policy

CASES=json.loads((Path(__file__).resolve().parents[1]/'bench/u109-self-inspection.json').read_text())['development']

@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
def test_recognizable_own_requests_read_installed_source(case,monkeypatch):
    from cursiv_engine.core import file_access
    monkeypatch.setattr(file_access,'perform',lambda *a,**k:pytest.fail('Own-source requests must not read the user workspace'))
    packet=own.prepare(case['question'])
    assert packet is not None,'Own-source dispatch did not start'
    if case['id']=='missing':
        assert packet.status=='NOT FOUND IN SEARCHED SCOPE'
        return
    assert not packet.error,packet.error
    assert packet.snippets,'No successful-looking empty inspection'
    if 'path' in case:assert case['path'] in {s.path for s in packet.snippets}

def test_startup_is_not_a_same_named_review_or_prompt_helper():
    p=own.prepare(CASES[0]['question'])
    assert p is not None and not p.error
    assert any(s.path=='launcher/main.py' and s.symbol=='main' for s in p.snippets)

def test_coverage_counts_real_reads_not_whole_index(monkeypatch):
    read=self_index.text;seen=[]
    def observed(*a):seen.append(a[2]);return read(*a)
    monkeypatch.setattr(self_index,'text',observed)
    p=own.prepare('Trace what happens when I submit a message in Cursiv.')
    assert p is not None and not p.error
    assert p.coverage['successful_reads']==len(seen)>0
    assert p.coverage['successful_reads']<p.indexed_files
    assert p.coverage['scope']=='installed_application'

def test_missing_search_is_not_absence_of_functionality():
    p=own.prepare('Find your implementation of the nonexistent frobnicator engine.')
    assert p is not None
    assert p.status=='NOT FOUND IN SEARCHED SCOPE'
    assert 'does not exist' not in p.footer()

@pytest.mark.parametrize('answer',[
    'Cursiv cannot process PDFs.',
    'There is no persistent memory implementation.',
    'Cursiv does not support copying portable workspaces to an external SSD.',
    'The desktop entry point is cursiv_engine/chat/review.py::prepare.',
])
def test_unsupported_conclusions_are_not_accepted(answer):
    token=own._active.set(own.prepare('Trace what happens when I submit a message in Cursiv.'))
    try:assert own.problems(answer)
    finally:own._active.reset(token)

def test_regex_claim_is_checked_deterministically():
    p=own.prepare(CASES[-2]['question'])
    assert p is not None and not p.error
    assert any(f.get('kind')=='regex' and f.get('matched') is True for f in p.technical)

def test_empty_explicit_workspace_inspection_is_actionable(tmp_path):
    out=source_inspection.investigate('Inspect my repository source code.',tmp_path).text
    assert 'NOT FOUND IN SEARCHED SCOPE' in out
    assert 'No source files were read' in out

def test_no_tools_does_not_load_index(monkeypatch):
    monkeypatch.setattr(self_index,'load',lambda *a:pytest.fail('No source reads when denied'))
    p=own.prepare('No tools. Inspect your source code.')
    assert p is not None and p.error

def test_ordinary_chat_does_not_load_index(monkeypatch):
    monkeypatch.setattr(self_index,'load',lambda *a:pytest.fail('Ordinary chat must not parse the source index'))
    assert own.prepare('Hello, how are you today?') is None

def test_explicit_other_repository_keeps_workspace_boundary():
    assert own.prepare('Inspect my repository and trace its PDF importer.') is None
