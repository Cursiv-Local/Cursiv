"""Field Station sign-in, sessions, CSRF, rate limits, first-run setup and encryption unlock
(cursiv_engine/station/sessions.py). Real accounts and real encryption, in temporary folders."""
import pytest

from cursiv_engine.station import sessions as ss


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def test_sessions_expire_when_idle_and_absolutely():
    c = Clock()
    s = ss.Sessions(clock=c)
    a = s.new("ana", "192.168.4.20")
    assert s.get(a["token"])["user"] == "ana"
    c.t += ss.IDLE_S + 1
    assert s.get(a["token"]) is None                          # idle too long
    b = s.new("ana", "x")
    for _ in range(ss.ABSOLUTE_S // (ss.IDLE_S - 60) + 1):     # kept active, but past the absolute limit
        c.t += ss.IDLE_S - 60
        s.get(b["token"])
    assert s.get(b["token"]) is None
    assert s.get(None) is None and s.get("forged") is None


def test_tokens_are_random_and_csrf_is_per_session():
    s = ss.Sessions()
    a, b = s.new("ana", "x"), s.new("ana", "x")
    assert a["token"] != b["token"] and a["csrf"] != b["csrf"] and len(a["token"]) >= 40
    assert ss.Sessions.csrf_ok(a, a["csrf"]) and not ss.Sessions.csrf_ok(a, b["csrf"])
    assert not ss.Sessions.csrf_ok(a, None) and not ss.Sessions.csrf_ok(a, "")
    s.end(a["token"])
    assert s.get(a["token"]) is None


def test_the_limiter_waits_after_free_tries_and_doubles():
    c = Clock()
    lim = ss.Limiter(clock=c)
    for _ in range(ss.FREE_TRIES - 1):
        lim.fail("ip:1")
    assert lim.wait("ip:1") == 0
    lim.fail("ip:1")
    first = lim.wait("ip:1")
    assert ss.FIRST_WAIT_S <= first <= ss.FIRST_WAIT_S + 1
    c.t += first
    lim.fail("ip:1")
    assert lim.wait("ip:1") > first                            # doubled
    lim.clear("ip:1")
    assert lim.wait("ip:1") == 0


@pytest.fixture
def station(tmp_path, monkeypatch):
    """A fresh station: no accounts, no encryption, its data in temporary folders."""
    from cursiv_engine.core import vault
    from cursiv_engine.guardian import access_gate as ag
    rt = tmp_path / "runtime"
    monkeypatch.setattr(ag, "_RUNTIME", rt)
    for name in ("_HASH_FILE", "_META_FILE", "_FLAG_FILE", "_ACCOUNTS_FILE"):
        monkeypatch.setattr(ag, name, rt / getattr(ag, name).name)
    data = tmp_path / "data"
    (data / "fieldlog").mkdir(parents=True)
    (data / "fieldlog" / "observations.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setattr(vault, "roots", lambda: [data.absolute()])
    vault.lock()
    yield ss.Gate(), data
    vault.lock()


def test_first_setup_needs_the_console_code_then_encrypts_and_creates_the_admin(station):
    gate, data = station
    assert gate.needs_setup()
    with pytest.raises(PermissionError, match="setup code"):
        gate.first_setup("00000000" if gate.setup_code != "00000000" else "1", "lead", "password1",
                         "a long passphrase", "192.168.4.20")
    with pytest.raises(ValueError, match="different"):
        gate.first_setup(gate.setup_code, "lead", "same-thing-12", "same-thing-12", "192.168.4.20")
    code = gate.setup_code
    gate.first_setup(code, "lead", "password1", "a long passphrase", "192.168.4.20")
    assert not gate.needs_setup() and gate.setup_code != code       # spent
    assert gate.encryption() == {"encrypted": True, "unlocked": True}
    with pytest.raises(PermissionError, match="already"):
        gate.first_setup(gate.setup_code, "mallory", "password2", "another passphrase", "192.168.4.66")


def test_guessing_the_setup_code_is_slowed_down(station):
    gate, _ = station
    for _ in range(ss.FREE_TRIES):
        with pytest.raises(PermissionError):
            gate.first_setup("wrong", "x", "password1", "a long passphrase", "10.0.0.9")
    with pytest.raises(ss.TooMany):
        gate.first_setup(gate.setup_code, "x", "password1", "a long passphrase", "10.0.0.9")


def test_sign_in_uses_cursiv_accounts_and_slows_guessing(station):
    gate, _ = station
    gate.first_setup(gate.setup_code, "lead", "password1", "a long passphrase", "127.0.0.1")
    assert gate.sign_in("lead", "password1", "192.168.4.20")
    for _ in range(ss.FREE_TRIES):
        assert not gate.sign_in("lead", "wrong", "192.168.4.21")
    with pytest.raises(ss.TooMany):                       # the right password waits too, from that address
        gate.sign_in("lead", "password1", "192.168.4.21")
    with pytest.raises(ss.TooMany):                       # and for that account, from anywhere
        gate.sign_in("lead", "password1", "192.168.4.99")


def test_after_a_boot_the_data_stays_locked_until_the_passphrase(station):
    from cursiv_engine.core import vault
    gate, _ = station
    gate.first_setup(gate.setup_code, "lead", "password1", "a long passphrase", "127.0.0.1")
    vault.lock()                                          # what a reboot leaves
    assert gate.encryption() == {"encrypted": True, "unlocked": False}
    with pytest.raises(vault.VaultError):
        gate.unlock("not the passphrase", "lead", "192.168.4.20")
    assert gate.encryption()["unlocked"] is False
    gate.unlock("a long passphrase", "lead", "192.168.4.20")
    assert gate.encryption() == {"encrypted": True, "unlocked": True}
