"""
Who may use the Field Station, and for how long (docs/FIELD-STATION-PLAN.md, phase 3).

- Sign-in uses the existing Cursiv accounts (guardian/access_gate.py). Being on the station's Wi-Fi
  authorizes nothing by itself.
- A session is a random token in an HttpOnly, SameSite=Strict cookie, with an idle limit and an absolute
  limit. Each session has its own CSRF token, required on every request that changes something.
- Wrong passwords and wrong encryption passphrases are slowed down per client address and per account:
  after FREE_TRIES, a wait that doubles up to MAX_WAIT_S. The same limiter covers the setup code.
- The notebook (and memory) stay encrypted after a boot until a signed-in person enters the encryption
  passphrase (vault.unlock), as the desktop asks at start. Until then only telemetry is served.
- First-run setup (no account yet) needs the one-time setup code the station prints on its own console,
  so the first person to join the Wi-Fi can't make themselves administrator.
"""
from __future__ import annotations

import hmac
import secrets
import threading
import time

IDLE_S = 30 * 60
ABSOLUTE_S = 12 * 3600
FREE_TRIES = 5
FIRST_WAIT_S = 30
MAX_WAIT_S = 15 * 60


class Limiter:
    """Counts failures per key (a client address, an account). Successful sign-in clears the account's."""

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._rows: dict[str, dict] = {}
        self._lock = threading.Lock()

    def wait(self, *keys: str) -> int:
        now = self._clock()
        with self._lock:
            return max([0] + [int(r["until"] - now) + 1 for k in keys
                              if (r := self._rows.get(k)) and r["until"] > now])

    def fail(self, *keys: str) -> None:
        now = self._clock()
        with self._lock:
            for k in keys:
                r = self._rows.setdefault(k, {"n": 0, "until": 0.0})
                r["n"] += 1
                extra = r["n"] - FREE_TRIES + 1
                r["until"] = now + min(MAX_WAIT_S, FIRST_WAIT_S * 2 ** (extra - 1)) if extra > 0 else 0.0

    def clear(self, *keys: str) -> None:
        with self._lock:
            for k in keys:
                self._rows.pop(k, None)


class TooMany(Exception):
    def __init__(self, wait: int):
        super().__init__(f"Too many wrong tries. Wait {wait // 60} min {wait % 60} s.")
        self.wait = wait


class Sessions:
    def __init__(self, clock=time.time):
        self._clock = clock
        self._by_token: dict[str, dict] = {}
        self._lock = threading.Lock()

    def new(self, user: str, client: str) -> dict:
        now = self._clock()
        s = {"token": secrets.token_urlsafe(32), "csrf": secrets.token_urlsafe(32), "user": user,
             "client": client, "created": now, "last": now}
        with self._lock:
            self._by_token[s["token"]] = s
        return s

    def get(self, token: str | None) -> dict | None:
        if not token:
            return None
        now = self._clock()
        with self._lock:
            s = self._by_token.get(token)
            if s is None:
                return None
            if now - s["last"] > IDLE_S or now - s["created"] > ABSOLUTE_S:
                del self._by_token[token]
                return None
            s["last"] = now
            return s

    def end(self, token: str | None) -> None:
        with self._lock:
            self._by_token.pop(token or "", None)

    def end_all(self) -> None:
        with self._lock:
            self._by_token.clear()

    @staticmethod
    def csrf_ok(session: dict, supplied: str | None) -> bool:
        return bool(supplied) and hmac.compare_digest(session["csrf"], supplied)


class Gate:
    """Sign-in, setup and unlock, with the limiter in front of every secret."""

    def __init__(self, clock=time.monotonic):
        self.limiter = Limiter(clock)
        self.setup_code = f"{secrets.randbelow(10**8):08d}"

    # accounts
    @staticmethod
    def needs_setup() -> bool:
        from cursiv_engine.guardian import access_gate
        return not access_gate.is_setup_complete()

    def sign_in(self, username: str, password: str, client: str) -> bool:
        from cursiv_engine.guardian import access_gate
        keys = (f"ip:{client}", f"user:{username.casefold()}")
        wait = self.limiter.wait(*keys)
        if wait:
            raise TooMany(wait)
        try:
            ok = bool(username) and bool(password) and access_gate.verify_credentials(username, password)
        except access_gate.AccountsUnreadable:
            raise
        if ok:
            self.limiter.clear(*keys)
        else:
            self.limiter.fail(*keys)
        return ok

    def first_setup(self, code: str, username: str, password: str, passphrase: str, client: str,
                    station_name: str = "Field station") -> None:
        """Create the administrator account, encrypt this station's data and name its notebook (so its entries
        show a name, not an id, in team views). Only while no account exists, and only with the console's
        setup code."""
        from cursiv_engine.guardian import access_gate
        from cursiv_engine.core import vault_migration
        keys = (f"ip:{client}", "setup")
        wait = self.limiter.wait(*keys)
        if wait:
            raise TooMany(wait)
        if not self.needs_setup():
            raise PermissionError("this station already has an administrator")
        if not hmac.compare_digest(self.setup_code, (code or "").strip()):
            self.limiter.fail(*keys)
            raise PermissionError("that setup code isn't right; it's shown on the station's console")
        if len(password) < 8 or len(passphrase) < 12:
            raise ValueError("use a password of at least 8 characters and a passphrase of at least 12")
        if password == passphrase:
            raise ValueError("the encryption passphrase must be different from the sign-in password")
        from cursiv_engine.core import fieldlog
        station_name = fieldlog.clean_name(station_name or "Field station")
        vault_migration.migrate(passphrase)           # encrypt first: no account exists without it
        access_gate.setup_credentials(username, password)
        fieldlog.set_name(station_name)
        self.setup_code = f"{secrets.randbelow(10**8):08d}"   # spent

    # encryption
    @staticmethod
    def encryption() -> dict:
        from cursiv_engine.core import vault
        roots = [r for r in vault.roots() if (r / vault.MARKER).exists()]
        return {"encrypted": bool(roots), "unlocked": bool(roots) and all(r in vault._keys for r in roots)}

    def unlock(self, passphrase: str, user: str, client: str) -> int:
        """Unlock with the encryption passphrase; returns how many newer stores were encrypted on the way."""
        from cursiv_engine.core import vault, vault_migration
        keys = (f"ip:{client}", f"unlock:{user.casefold()}")
        wait = self.limiter.wait(*keys)
        if wait:
            raise TooMany(wait)
        try:
            vault.unlock(passphrase)
        except vault.VaultError:
            self.limiter.fail(*keys)
            raise
        self.limiter.clear(*keys)
        return vault_migration.adopt_new_stores()     # as the desktop does after unlocking (U98)
