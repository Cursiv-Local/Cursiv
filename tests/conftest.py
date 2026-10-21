"""Shared setup for Cursiv's tests (pytest loads this automatically)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "launcher")):
    if p not in sys.path:
        sys.path.insert(0, p)

# Qt windows are built off-screen; tests never show anything.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Building the chat window never starts the real AI engine in a test.
os.environ["CURSIV_NO_ENGINE_START"] = "1"

# Optional add-ons from a sibling Winkler_Codex_AI checkout are not part of
# these tests (and reading them from OneDrive can stall an import).
for _m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(_m, None)


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _memory_isolated(tmp_path, monkeypatch):
    """Background learning must not outlive a test's storage redirections.

The baseline suite changed the copied app's memory during an unrelated test.
Tests exercise learner work explicitly; ordinary chat tests never start jobs.
"""
    from cursiv_v215.memory import semantic, formation
    folder = tmp_path / 'memory'
    for key, value in (('CURSIV_DIR', folder), ('FACTS_FILE', folder / 'memory_facts.jsonl'),
                       ('SETTINGS_FILE', folder / 'memory_settings.json'),
                       ('EMB_CACHE_FILE', folder / 'embeddings_cache.json')):
        monkeypatch.setattr(semantic, key, value)
    monkeypatch.setattr(semantic, '_person', semantic.SHARED)
    monkeypatch.setattr(semantic, '_generation', 0)
    monkeypatch.setattr(semantic, '_embed_ok', False)
    monkeypatch.setattr(semantic, '_emb_cache', {})
    from cursiv_v215.memory import projects
    from cursiv_v215.core import style
    from cursiv_v215.coding import brain
    monkeypatch.setattr(projects, 'DIR', folder / 'projects')
    monkeypatch.setattr(style, 'DIR', folder / 'style')
    monkeypatch.setattr(brain, 'CURSIV_DIR', folder)
    monkeypatch.setattr(brain, 'PROFILE_FILE', folder / 'coding_profile.json')
    monkeypatch.setattr(brain, 'LESSONS_FILE', folder / 'coding_lessons.jsonl')
    monkeypatch.setattr(formation, '_logger', None)
    from cursiv_v215.core import curiosity, presence
    monkeypatch.setattr(curiosity, 'path', lambda person: folder / 'curiosity' / (person + '.json'))
    monkeypatch.setattr(presence, 'path', lambda person: folder / 'presence' / (person + '.json'))
    real_submit = formation.submit
    monkeypatch.setattr(formation, 'submit', lambda work, event_id: False)
    # No diagnostic file handler opens in a unit test unless explicitly tested.
    monkeypatch.setattr(formation, 'record', lambda stage, error=None: formation._counts.update([stage]))
    yield real_submit


def _real_data_state(watched=None):
    """The person's real records a test must never create or change."""
    from cursiv_v215.core import paths
    home = Path.home() / ".cursiv"
    out = {}
    for p in (watched if watched is not None else (
            home / "fieldlog", home / "fieldlog" / "observations.jsonl", home / "device_key.json",
            paths.APP_DATA / "memory_facts.jsonl", paths.APP_DATA / "config.json",
            paths.APP_DATA / 'memory_settings.json', paths.APP_DATA / 'embeddings_cache.json')):
        try:
            st = p.stat()
            out[str(p)] = (st.st_size, st.st_mtime_ns)
        except OSError:
            out[str(p)] = None
    return out


@pytest.fixture(autouse=True)
def _real_data_untouched():
    """Fails any test that writes to the real field log, signing key or memory (a test that undid
    its own redirection once pointed at them)."""
    before = _real_data_state()
    yield
    after = _real_data_state(Path(p) for p in before)    # portable tests can change HOME mid-test
    changed = [p for p in before if before[p] != after[p]]
    assert not changed, f"this test touched real data: {changed}"


@pytest.fixture(autouse=True)
def _signing_key_in_tmp(tmp_path_factory, monkeypatch):
    """Never create or use the real installation key (~/.cursiv/device_key.json) in a test."""
    from cursiv_v215.core import devicekey
    folder = tmp_path_factory.mktemp("devicekey")
    monkeypatch.setattr(devicekey, "key_file", lambda: folder / "device_key.json")
    devicekey._cache.clear()
    yield
    devicekey._cache.clear()
