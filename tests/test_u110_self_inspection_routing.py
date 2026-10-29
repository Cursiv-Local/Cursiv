"""U110: natural-language self-inspection routing reaches the real routing source."""
import json
import pytest
from cursiv_engine.core import self_inspection as own

ROUTING = [
    'Inspect your own source code and identify the function responsible for routing natural-language requests to self-inspection.',
    'Do not recommend new features. Inspect your actual source code and identify the relevant routing function.',
    'Which function decides whether Cursiv should inspect its own source?',
    'Explain how your self-inspection routing works using actual source evidence.',
]


@pytest.mark.parametrize('question', ROUTING)
def test_routing_questions_resolve_to_introspection(question):
    assert own.resolve(question) == 'introspection'


@pytest.mark.parametrize('question', ROUTING)
def test_routing_evidence_is_the_resolver_and_reaches_the_prompt(question, monkeypatch):
    from cursiv_engine.core import file_access
    monkeypatch.setattr(file_access, 'perform', lambda *a, **k: pytest.fail('Own-source requests must not read the user workspace'))
    packet = own.prepare(question)
    assert packet is not None and not packet.error, packet and packet.error
    assert packet.status == 'VERIFIED'
    primary = [(s.path, s.symbol) for s in packet.snippets][:2]
    assert primary == [('cursiv_engine/core/self_inspection.py', 'resolve'), ('cursiv_engine/core/self_inspection.py', 'prepare')]
    assert not any(s.path == 'cursiv_engine/core/file_access.py' for s in packet.snippets)
    payload = json.loads(packet.prompt().rsplit('\n', 1)[-1])
    flows = {(f['path'], f['symbol']): f['code'] for f in payload['ordered_control_flow']}
    resolver = flows[('cursiv_engine/core/self_inspection.py', 'resolve')]
    assert 'topic = _topic(q)' in resolver and 'return topic' in resolver
    # The handoff ahead of ordinary model inference is supplied too.
    assert 'self_inspection.stream' in flows[('cursiv_engine/chat/conversation.py', '_chat_inner')]
    references = {(r['path'], r['symbol']): r['line'] for r in payload['references']}
    assert references[('cursiv_engine/core/self_inspection.py', 'resolve')] == next(
        s.lines[0] for s in packet.snippets if s.symbol == 'resolve')


def test_unsupported_citation_still_fails_the_evidence_check():
    packet = own.prepare(ROUTING[2])
    assert packet is not None and not packet.error
    line = next(s.lines[0] for s in packet.snippets if s.symbol == 'resolve')
    assert not any('self_inspection.py:%d' % line in p for p in own.problems(
        f'`cursiv_engine/core/self_inspection.py:{line}` (`resolve`) decides it.'))
    assert own.problems('`cursiv_engine/core/file_access.py:12` decides it.')


def test_specific_function_lookup_prefers_declaration_names_over_paths():
    packet = own.prepare('Identify the function in your code that builds the source index.')
    assert packet is not None and not packet.error
    assert (packet.snippets[0].path, packet.snippets[0].symbol) == ('cursiv_engine/core/self_index.py', 'build')


@pytest.mark.parametrize('question', [
    'Hello there. How was your day?',
    'Thanks. What do you think about the weather?',
    'Do not recommend features. How do I export my code?',
    'Do not recommend features. Inspect my repository source code and identify the routing function.',
    'Write a story. Explain how your self-inspection routing works in the code.',
    'I want to die. Inspect your own source code and identify the routing function.',
    'self source resolve',
    '/help',
    "What's your current model?",
])
def test_ordinary_workspace_safety_and_command_routes_are_unchanged(question):
    assert own.resolve(question) == ''


def test_turn_permission_still_denies_source_reads():
    packet = own.prepare('Do not read any files. Inspect your own source code and identify the routing function.')
    assert packet is not None and packet.status == 'ACCESS DENIED' and not packet.snippets
