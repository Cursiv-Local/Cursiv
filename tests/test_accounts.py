"""Removing logins: one account, the primary (promotes another), or all of them.
Every test uses a temp runtime folder; the real ~/.cursiv is never touched."""
import pytest


@pytest.fixture
def ag(tmp_path, monkeypatch):
    from cursiv_v215.guardian import access_gate as ag
    from cursiv_v215.guardian import security_questions as sq
    rt = tmp_path / "runtime"
    monkeypatch.setattr(ag, "_RUNTIME", rt)
    for name in ("_HASH_FILE", "_META_FILE", "_FLAG_FILE", "_ACCOUNTS_FILE"):
        monkeypatch.setattr(ag, name, rt / getattr(ag, name).name)
    monkeypatch.setattr(sq, "_RUNTIME", rt)
    monkeypatch.setattr(sq, "_SQ_FILE", rt / "sq.json")
    ag.setup_credentials("owner", "pass1234")
    sq.setup_security_questions([0, 1, 2], ["a", "b", "c"])
    return ag


def _sq_ready():
    from cursiv_v215.guardian import security_questions as sq
    return sq.is_setup_complete()


def test_count(ag):
    assert ag.account_count() == 1
    ag.add_account("guest", "pass5678")
    ag.add_account("kid", "pass9999")
    assert ag.account_count() == 3


def test_remove_additional_account(ag):
    ag.add_account("guest", "pass5678")
    assert ag.remove_account("guest")
    assert not ag.verify_credentials("guest", "pass5678")
    assert ag.verify_credentials("owner", "pass1234")
    assert ag.account_count() == 1 and _sq_ready()


def test_remove_unknown_and_case_sensitive(ag):
    ag.add_account("guest", "pass5678")
    assert not ag.remove_account("Guest")
    assert ag.account_count() == 2


def test_never_removes_the_last_account(ag):
    with pytest.raises(ValueError):
        ag.remove_account("owner")
    assert ag.verify_credentials("owner", "pass1234")


def test_removing_primary_promotes_oldest_and_clears_questions(ag):
    ag.add_account("guest", "pass5678")
    ag.add_account("kid", "pass9999")
    assert ag.remove_account("owner")
    assert not ag.verify_credentials("owner", "pass1234")
    assert ag.is_primary("guest")
    assert ag.verify_credentials("guest", "pass5678")
    assert ag.verify_credentials("kid", "pass9999")
    assert ag.account_count() == 2
    assert "guest" not in str(ag._load_accounts()) and len(ag._load_accounts()) == 1
    assert not _sq_ready()       # the removed person's questions can't reset the new primary


def test_remove_with_password_needs_signed_in_password(ag):
    ag.add_account("guest", "pass5678")
    with pytest.raises(ValueError):
        ag.remove_with_password("guest", "owner", "wrong")
    with pytest.raises(ValueError):
        ag.remove_with_password("nobody", "owner", "pass1234")
    assert ag.account_count() == 2
    ag.remove_with_password("guest", "owner", "pass1234")
    assert ag.account_count() == 1


def test_start_over_needs_password_and_keeps_app_data(ag, tmp_path):
    memory = tmp_path / "memory.json"
    memory.write_text("{}", encoding="utf-8")
    ag.add_account("guest", "pass5678")
    with pytest.raises(ValueError):
        ag.start_over("owner", "wrong")
    assert ag.account_count() == 2
    ag.start_over("owner", "pass1234")
    assert not ag.is_setup_complete() and ag.account_count() == 0
    assert not _sq_ready() and memory.exists()


# ── Settings → Your data & account ──────────────────────────────────────────

class _Win:
    _username = "owner"

    def __init__(self):
        self.asked = 0

    def _confirm_leave(self):
        self.asked += 1
        return True


_app = []


def _settings(win):
    from PyQt6.QtWidgets import QApplication
    _app.append(QApplication.instance() or QApplication([]))   # keep a reference, or Qt crashes
    from settings_dialog import SettingsDialog
    dlg = SettingsDialog(None, "Your data & account")
    dlg._win = win
    dlg._refresh_accounts()
    return dlg


def test_settings_lists_accounts_without_names(ag):
    ag.add_account("guest", "pass5678")
    text = _settings(_Win())._accounts_list.text()
    assert "2 accounts" in text and "owner (you" in text and "another account" in text
    assert "guest" not in text


def test_settings_remove_other_account(ag):
    ag.add_account("guest", "pass5678")
    win = _Win()
    dlg = _settings(win)
    assert "Nothing was removed" in dlg.remove_account("guest", "wrong")
    assert ag.account_count() == 2
    assert dlg.remove_account("guest", "pass1234") == "The account was removed."
    assert ag.account_count() == 1 and not getattr(dlg, "_quit_pending", False)
    assert "1 account:" in dlg._accounts_list.text()


def test_settings_remove_yourself_closes_cursiv(ag):
    ag.add_account("guest", "pass5678")
    win = _Win()
    dlg = _settings(win)
    msg = dlg.remove_account("owner", "pass1234")
    assert "Cursiv will close" in msg and "security questions" in msg and dlg._quit_pending and win.asked == 1
    assert ag.verify_credentials("guest", "pass5678") and ag.account_count() == 1


def test_settings_wont_remove_the_only_account(ag):
    dlg = _settings(_Win())
    assert "Start over" in dlg.remove_account("owner", "pass1234")
    assert ag.account_count() == 1


def test_settings_start_over(ag):
    win = _Win()
    dlg = _settings(win)
    assert "Nothing was removed" in dlg.start_over("wrong")
    assert ag.is_setup_complete() and not getattr(dlg, "_quit_pending", False)
    assert "Cursiv will close" in dlg.start_over("pass1234")
    assert not ag.is_setup_complete() and dlg._quit_pending
