"""Login files survive a power cut and are never silently read as "no accounts" (U101 review)."""
import pytest


@pytest.fixture
def ag(tmp_path, monkeypatch):
    from cursiv_engine.guardian import access_gate as ag
    rt = tmp_path / "runtime"
    monkeypatch.setattr(ag, "_RUNTIME", rt)
    for name in ("_HASH_FILE", "_META_FILE", "_FLAG_FILE", "_ACCOUNTS_FILE"):
        monkeypatch.setattr(ag, name, rt / getattr(ag, name).name)
    ag.setup_credentials("owner", "pass1234")
    ag.add_account("sam", "sampass99")
    ag.add_account("lee", "leepass99")
    return ag


def test_login_files_are_written_atomically(ag, monkeypatch):
    from cursiv_engine.core import atomic
    written = []
    real = atomic.write_bytes
    monkeypatch.setattr(atomic, "write_bytes", lambda path, data, **kw: (written.append((path.name, kw)), real(path, data, **kw)))
    ag.reset_password("newpass123", "owner")
    ag.add_account("kim", "kimpass99")
    assert ("auth.hash", {"protect": False}) in written and ("accounts.json", {"protect": False}) in written


def test_a_damaged_accounts_file_falls_back_to_the_last_good_copy(ag):
    # Was: json error -> {} -> the added accounts silently vanished.
    ag._ACCOUNTS_FILE.write_text('{"half a fi', encoding="utf-8")       # what a power cut can leave
    assert ag.verify_credentials("sam", "sampass99")
    assert ag.account_count() == 3
    assert ag._parse(ag._ACCOUNTS_FILE)                                   # and the good copy was put back


def test_both_copies_damaged_is_an_error_not_an_empty_list(ag):
    ag._ACCOUNTS_FILE.write_text("garbage", encoding="utf-8")
    ag._backup().write_text("garbage", encoding="utf-8")
    with pytest.raises(ag.AccountsUnreadable):
        ag.verify_credentials("sam", "sampass99")
    assert ag.verify_credentials("owner", "pass1234")       # the primary login still works
    assert ag.is_setup_complete()                           # never offers Create Account over a setup


def test_start_over_removes_the_backup_too(ag):
    ag.reset_credentials()
    assert not ag._backup().exists() and not ag.is_setup_complete()
