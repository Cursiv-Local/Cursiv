"""Conversation-only requests cannot be converted into actions by a model."""
import pytest
from cursiv_engine.core import turn_policy as tp


@pytest.mark.parametrize('text', [
    "For now, don't inspect documents, save memories, or change anything. Just talk with me naturally.",
    "For now, don’t inspect documents, save memories, or change anything.",
    "Do not read files, write anything, or remember this.",
    "Thought experiment only: create a file and remember its contents.",
    "No tools. Tell me about yourself.",
])
def test_explicit_boundaries(text):
    policy = tp.for_text(text)
    assert policy.blocks('read_file') and policy.blocks('system_info')
    assert policy.blocks('create_file') and policy.blocks('SAVE_MEMORY')
    assert policy.blocks('some_plugin') and not policy.automatic_memory


def test_readonly_and_automatic_only_are_distinct():
    policy = tp.for_text('Read-only review of source.py.')
    assert not policy.blocks('read_file') and policy.blocks('write_file')
    automatic = tp.for_text("Don't automatically save memories, but remember manually: TEST-81")
    assert not automatic.automatic_memory and not automatic.blocks('SAVE_MEMORY')


@pytest.mark.parametrize('text', [
    'file create example.txt :: Do not inspect documents or save memories. Just talk.',
    'Create a file named example.txt containing: No tools. Never write.',
    'Remember permanently: Never inspect my documents.',
    'Explain the sentence "do not inspect files".',
    'I don’t read books. What should I try?',
    'What would happen if I asked you to remember something?',
])
def test_payloads_and_examples_are_not_instructions(text):
    assert tp.for_text(text) == tp.Policy()


def test_tool_planning_and_execution_both_enforce_limits(monkeypatch, tmp_path):
    from cursiv_engine.core import tools
    policy = tp.for_text('Just talk about my files.')
    monkeypatch.setattr(tools, 'system_info', lambda: pytest.fail('No inspection'))
    assert tools.plan('Just talk about my files.', lambda _: pytest.fail('No planner call')) == []
    outcome = tools.run([dict(tool='system_info', args={})], policy=policy)[0]
    assert not outcome.ok and 'No action' in outcome.output


def test_automatic_learning_respects_coordinated_negative():
    from cursiv_engine.memory import formation
    assert not formation.permitted("For now, don't inspect documents, save memories, or change anything.")


def test_native_file_and_memory_routes_respect_limits(tmp_path):
    from cursiv_engine.core import file_access
    from cursiv_engine.memory import intents
    result = file_access.command('Create new.txt containing: marker. Do not change anything.', [], tmp_path)
    assert result.receipts[0].ok  # The explicitly supplied file contents are data.
    denied = intents.command('Remember TEST-81, but do not save memories.', [], person='tester')
    assert denied is not None and not denied.ok and not denied.outcomes[0].records
