"""U103: storage code may not swallow errors silently.

A handler that only does `pass` / `continue` in the modules that keep the person's data must say why
on its `except` line (`# best-effort: ...`). The review found three that were hiding real failures:
a damaged territories file overwritten with defaults, a locked login file skipped during Start over,
and removed security answers left behind. Those now raise or keep the file; the tests below hold them."""
import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "cursiv_engine"
STORAGE = [
    "core/atomic.py", "core/vault.py", "core/vault_migration.py", "core/private_store.py",
    "core/fieldlog.py", "core/state_store.py", "core/strand.py", "core/strand_store.py",
    *sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "guardian").glob("*.py")),
    *sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "memory").glob("*.py")),
]


def _does_nothing(stmt) -> bool:
    return isinstance(stmt, (ast.Pass, ast.Continue)) or (
        isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is ...)


def _silent_handlers(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    for node in ast.walk(ast.parse("\n".join(lines))):
        if isinstance(node, ast.ExceptHandler) and all(_does_nothing(s) for s in node.body):
            yield node.lineno, lines[node.lineno - 1]


def test_storage_code_says_why_whenever_it_ignores_an_error():
    unexplained = [f"{name}:{n}: {line.strip()}" for name in STORAGE
                   for n, line in _silent_handlers(ROOT / name) if "# best-effort:" not in line]
    assert not unexplained, ("Silent error handlers in storage code; handle the error, or say why "
                             "ignoring it is safe with '# best-effort: <why>' on the except line:\n"
                             + "\n".join(unexplained))


def test_the_scan_covers_the_storage_modules():
    assert len(STORAGE) > 20 and all((ROOT / name).is_file() for name in STORAGE)
    assert any(_silent_handlers(ROOT / "memory/session_log.py"))      # it finds marked ones too


# ── the three it found ───────────────────────────────────────────────────────

def test_a_damaged_territories_file_is_moved_aside_not_overwritten(tmp_path, monkeypatch):
    from cursiv_engine.core import strand_store
    monkeypatch.setattr(strand_store, "CURSIV_DIR", tmp_path)
    monkeypatch.setattr(strand_store, "TERRITORIES_FILE", tmp_path / "territories.json")
    (tmp_path / "territories.json").write_text('{"mine": {"label": "My own', encoding="utf-8")
    assert strand_store.load_territories() == strand_store._DEFAULT_TERRITORIES
    kept = list(tmp_path.glob("territories.damaged-*.json"))
    assert len(kept) == 1 and kept[0].read_text(encoding="utf-8") == '{"mine": {"label": "My own'


@pytest.fixture
def ag(tmp_path, monkeypatch):
    from cursiv_engine.guardian import access_gate as ag, security_questions as sq
    rt = tmp_path / "runtime"
    monkeypatch.setattr(ag, "_RUNTIME", rt)
    for name in ("_HASH_FILE", "_META_FILE", "_FLAG_FILE", "_ACCOUNTS_FILE"):
        monkeypatch.setattr(ag, name, rt / getattr(ag, name).name)
    monkeypatch.setattr(sq, "_RUNTIME", rt)
    monkeypatch.setattr(sq, "_SQ_FILE", rt / "sq.json")
    ag.setup_credentials("owner", "pass1234")
    ag.add_account("sam", "sampass99")
    return ag


def test_start_over_says_so_when_a_login_file_is_locked(ag, monkeypatch):
    real = Path.unlink

    def locked(self, missing_ok=False):
        if self.name == "accounts.json":
            raise PermissionError(13, "The file is in use")
        return real(self, missing_ok=missing_ok)
    monkeypatch.setattr(Path, "unlink", locked)
    with pytest.raises(OSError, match="accounts.json"):
        ag.reset_credentials()
    assert not ag._HASH_FILE.exists()                 # the rest were still removed


def test_removing_an_account_stops_if_its_security_answers_cannot_be_removed(ag, monkeypatch):
    from cursiv_engine.core import atomic
    from cursiv_engine.guardian import security_questions as sq
    sq.setup_security_questions([0, 1, 2], ["a", "b", "c"], "sam")

    def full_disk(*a, **k):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(atomic, "write_bytes", full_disk)
    with pytest.raises(OSError):
        ag.remove_account("sam")
    assert ag.username_exists("sam")                   # nothing half-done: the login is still there
    assert sq.is_setup_complete("sam")


def test_security_answers_are_saved_atomically(ag, monkeypatch):
    from cursiv_engine.core import atomic
    from cursiv_engine.guardian import security_questions as sq
    written = []
    real = atomic.write_bytes
    monkeypatch.setattr(atomic, "write_bytes", lambda p, d, **k: (written.append(Path(p).name), real(p, d, **k)))
    sq.setup_security_questions([0, 1, 2], ["a", "b", "c"], "owner")
    assert "sq.json" in written and json.loads((ag._RUNTIME / "sq.json").read_text(encoding="utf-8"))["accounts"]
