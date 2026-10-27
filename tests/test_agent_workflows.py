"""Research profiles through the actual desktop command boundary, with synthetic evidence."""
import pytest

from cursiv_engine.agents import custom
from cursiv_engine.core import fieldlog


@pytest.fixture
def agent_runtime(tmp_path, monkeypatch):
    import chat_commands as cc
    monkeypatch.setattr(custom, 'DIR', tmp_path / 'agents')
    monkeypatch.setattr(fieldlog, 'log_dir', lambda: tmp_path / 'notebook')
    calls = []
    def generate(messages, cfg, **kwargs):
        calls.append(messages)
        # The transport boundary is explicit in the repaired runtime's test adapter.
        try:
            from cursiv_engine.chat import request_budget
        except ImportError:
            pass
        else:
            request_budget.attempt('synthetic', messages, kwargs.get('max_tokens', 300))
        return iter(['A short synthetic answer.']), ['synthetic']
    monkeypatch.setattr(cc, '_cascade_stream', generate)
    return cc, calls


def rendered(result):
    if result is None:
        return ''
    return ''.join(result.generator) if hasattr(result, 'generator') else result.text


@pytest.mark.parametrize('text', [
    'agents ask Write a short invitation.', 'AGENTS\tASK Write a short invitation.',
    'agent council Write a short invitation.', '@writer Write a short invitation.',
])
def test_public_agent_commands_execute_the_selected_role(agent_runtime, text):
    cc, calls = agent_runtime
    result = cc.handle_command(text, {}, [])
    assert 'synthetic answer' in rendered(result)
    assert len(calls) == 1                    # one writing task needs one profile, no synthesis


@pytest.mark.parametrize('text', ['agents ask', 'agent council', '@writer', '@missing',
                                  'agents ask @missing: Write an invitation.'])
def test_malformed_commands_are_actionable_without_a_model(agent_runtime, text):
    cc, calls = agent_runtime
    result = cc.handle_command(text, {}, [])
    assert result is not None
    assert any(word in rendered(result).lower() for word in ('question', 'message', 'unknown', 'no agent', 'usage'))
    assert not calls


def test_native_and_restricted_turn_boundaries_still_precede_agents(agent_runtime, monkeypatch):
    cc, calls = agent_runtime
    marker = cc.TextResult('native notebook receipt')
    monkeypatch.setattr(cc, 'notebook_command', lambda *a, **kw: marker)
    assert cc.handle_command('agents ask check my notebook', {}, []) is marker
    assert cc.handle_command('No tools this turn. @field inspect my notebook', {}, []) is None
    assert not calls


def test_group_budget_never_silently_drops_an_explicit_role(agent_runtime):
    cc, calls = agent_runtime
    result = cc.handle_command('agents ask @field,@checker,@protocol,@report: Review this.', {}, [])
    text = rendered(result)
    assert 'three' in text.lower() or '3' in text
    assert all('@' + name in text for name in ('field', 'checker', 'protocol', 'report'))
    assert not calls


def test_group_checker_receives_notebook_findings_without_model_work(agent_runtime):
    cc, calls = agent_runtime
    entry = fieldlog.add(site='Lake', sample_id='K-1', measurements=[{'name':'nitrate','value':'3.5','unit':''}])
    text = rendered(cc.handle_command('agents ask Check my notebook for missing units.', {}, []))
    assert entry['id'] in text and 'no unit' in text
    assert not calls
