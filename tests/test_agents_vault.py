"""U98: custom agents are encrypted with the vault, and their instructions are neutral."""
from pathlib import Path

import pytest

from cursiv_engine.agents import custom
from cursiv_engine.core import vault, vault_migration

PASSWORD = 'synthetic-agents-passphrase'


@pytest.fixture
def agents(tmp_path, monkeypatch):
    root = tmp_path / '.cursiv'
    root.mkdir()
    monkeypatch.setattr(custom, 'DIR', root / 'agents')
    monkeypatch.setattr(custom, '_person', lambda: 'tester')
    yield root
    vault.lock()


def test_agents_folder_is_covered():
    assert vault.covered(Path('agents/tester/chef.json'))


def test_agent_and_what_it_was_taught_are_encrypted(agents):
    vault_migration.migrate(PASSWORD, [agents])
    custom.create('chef', 'plans meals on a budget and asks about allergies')
    custom.teach('chef', 'Sam is allergic to peanuts')
    raw = (agents / 'agents' / 'tester' / 'chef.json').read_bytes()
    assert raw.startswith(vault.MAGIC) and b'peanuts' not in raw
    assert custom.load('chef')['knowledge'] == ['Sam is allergic to peanuts']
    assert [a['name'] for a in custom.all_agents()] == ['chef']
    vault.lock()
    with pytest.raises(vault.VaultError):
        custom.all_agents()                     # locked is never "no agents"


def test_existing_readable_agents_are_adopted_at_unlock(agents):
    (agents / 'memory.json').write_bytes(b'{}')
    vault_migration.migrate(PASSWORD, [agents])
    folder = agents / 'agents' / 'tester'
    folder.mkdir(parents=True)
    (folder / 'tutor.json').write_bytes(b'{"name": "tutor", "job": "explains maths", "knowledge": []}')
    assert vault_migration.adopt_new_stores([agents]) == 1
    assert custom.load('tutor')['job'] == 'explains maths'


def test_agent_instructions_are_neutral():
    prompt = custom.system_prompt({'name': 'chef', 'job': 'plans meals', 'knowledge': ['likes rice']})
    import re
    assert 'family' not in prompt.lower() and not re.search(r'\bhis\b', prompt)
    assert 'independent open-source project' in prompt and 'likes rice' in prompt
