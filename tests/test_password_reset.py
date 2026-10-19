"""Forgot password: each account has its own security questions, and a reset changes only
the password of the account that answered them. Temp runtime folder only."""
import json

import pytest


@pytest.fixture
def env(tmp_path, monkeypatch):
    from cursiv_v215.guardian import access_gate as ag
    from cursiv_v215.guardian import security_questions as sq
    rt = tmp_path / "runtime"
    monkeypatch.setattr(ag, "_RUNTIME", rt)
    for name in ("_HASH_FILE", "_META_FILE", "_FLAG_FILE", "_ACCOUNTS_FILE"):
        monkeypatch.setattr(ag, name, rt / getattr(ag, name).name)
    monkeypatch.setattr(sq, "_RUNTIME", rt)
    monkeypatch.setattr(sq, "_SQ_FILE", rt / "sq.json")
    ag.setup_credentials("owner", "ownerpass")
    sq.setup_security_questions([0, 1, 2], ["rex", "boston", "lincoln"], "owner")
    ag.add_account("guest", "guestpass")
    sq.setup_security_questions([3, 4, 5], ["smith", "civic", "elm"], "guest")
    return ag, sq


def test_each_account_answers_its_own_questions(env):
    ag, sq = env
    assert sq.get_selected_questions("owner")[0] != sq.get_selected_questions("guest")[0]
    assert sq.verify_answers(["rex", "boston", "x"], "owner")
    assert not sq.verify_answers(["rex", "boston", "lincoln"], "guest")     # owner's answers, guest's account
    assert sq.verify_answers(["Smith", "civic!", "x"], "guest")


def test_a_reset_changes_only_the_account_that_answered(env):
    ag, sq = env
    ag.reset_password("newguest", username="guest")
    assert ag.verify_credentials("guest", "newguest") and not ag.verify_credentials("guest", "guestpass")
    assert ag.verify_credentials("owner", "ownerpass")                           # untouched (the bug)
    ag.reset_password("newowner", username="owner")
    assert ag.verify_credentials("owner", "newowner") and ag.verify_credentials("guest", "newguest")
    with pytest.raises(ValueError):
        ag.reset_password("x1234", username="nobody")


def test_an_account_without_questions_can_t_be_reset_with_someone_elses(env):
    ag, sq = env
    ag.add_account("kid", "kidpass")
    assert not sq.is_setup_complete("kid")
    assert not sq.verify_answers(["rex", "boston", "lincoln"], "kid")
    assert sq.get_selected_questions("kid") == []


def test_a_question_file_from_before_belongs_to_the_first_account(env, tmp_path):
    ag, sq = env
    from cursiv_v215.guardian import security_questions as sqm
    old = {"questions": [0, 1, 2], "answers": json.loads(sqm._SQ_FILE.read_text())["accounts"][sqm._uhash("owner")]["answers"]}
    sqm._SQ_FILE.write_text(json.dumps(old))                                      # the old single-set format
    assert sq.is_setup_complete("owner") and sq.verify_answers(["rex", "boston", "x"], "owner")
    assert not sq.is_setup_complete("guest")
    sq.setup_security_questions([3, 4, 5], ["smith", "civic", "elm"], "guest")   # rewriting keeps the owner's
    data = json.loads(sqm._SQ_FILE.read_text())
    assert set(data) == {"accounts"} and sq.verify_answers(["rex", "boston", "x"], "owner")


def test_removing_an_account_removes_only_its_questions(env):
    ag, sq = env
    ag.remove_account("guest")
    assert sq.is_setup_complete("owner") and not sq.is_setup_complete("guest")
    ag.add_account("guest2", "pass2222")
    sq.setup_security_questions([6, 7, 8], ["a", "b", "c"], "guest2")
    ag.remove_account("owner")                                                   # guest2 becomes primary
    assert ag.is_primary("guest2")
    assert sq.is_setup_complete("guest2") and not sq.is_setup_complete("owner")
    assert not sq.verify_answers(["rex", "boston", "lincoln"])                   # the old owner's can't reset the new primary


def test_the_reset_dialog_sends_the_typed_username(env, monkeypatch):
    """The Forgot password window resets the typed account, with that account's questions."""
    import login_dialog
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    ag, sq = env
    d = login_dialog.ResetPasswordDialog()
    d._p0_user.setText("guest")
    d._p0_submit()
    assert d._stack.currentIndex() == 1 and d._q_labels[0].text() == sq.QUESTIONS[3]
    for f, a in zip(d._sq_fields, ["smith", "civic", "elm"]):
        f.setText(a)
    d._p1_submit()
    d._new_pw.setText("brandnew"); d._new_pw2.setText("brandnew")
    d._p2_submit()
    assert ag.verify_credentials("guest", "brandnew") and ag.verify_credentials("owner", "ownerpass")
    d2 = login_dialog.ResetPasswordDialog()
    ag.add_account("kid", "kidpass")
    d2._p0_user.setText("kid")
    d2._p0_submit()
    assert d2._stack.currentIndex() == 0 and "no security questions" in d2._p0_err.text()
    assert app is not None
