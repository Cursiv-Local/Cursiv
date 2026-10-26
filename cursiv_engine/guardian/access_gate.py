"""
Cursiv Access Gate — bcrypt credential system.
Phase slot: Structure / Security & Access

Storage:
  .cursiv/runtime/auth.hash   — bcrypt hash of the password (64 bytes, safe to store)
  .cursiv/runtime/auth.meta   — SHA-256 of username (no password info)
  .cursiv/runtime/auth.ini    — setup marker

Security model:
  bcrypt is a one-way function. The original password cannot be recovered from the
  stored hash under any circumstances. An attacker who steals auth.hash gains nothing
  actionable — they still cannot log in or recover the password without brute-forcing
  every possible input at ~250ms per attempt (enforced by rounds=12).

  This is strictly stronger than any fragmentation/distribution scheme, which only
  delays recovery rather than preventing it.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    import bcrypt
    _BCRYPT_OK = True
except ImportError:
    _BCRYPT_OK = False

_RUNTIME   = Path.home() / ".cursiv" / "runtime"
# Deliberately NOT Path(__file__).parent.parent.parent — under a frozen
# PyInstaller build, __file__ resolves inside the install directory, and
# every installer version installs to the same fixed path ({autopf}\Cursiv,
# no version number). That meant credential files from any earlier test
# install silently persisted across reinstalls/upgrades, so is_setup_complete()
# stayed True forever and the app skipped straight to Login, never showing
# Create Account again. Path.home() is stable regardless of install location
# or version.
_HASH_FILE = _RUNTIME / "auth.hash"    # bcrypt hash (64 bytes) -- primary account only
_META_FILE = _RUNTIME / "auth.meta"    # SHA-256 of username (hex string) -- primary account only
_FLAG_FILE = _RUNTIME / "auth.ini"     # setup marker

# Additional accounts (beyond the first) live here instead -- the primary
# account's storage above is left completely untouched so multi-account
# support carries zero risk to the login that's already working. Format:
# {"<sha256 username hex>": {"pw_hash": "<base64 bcrypt hash>", "created": "<iso timestamp>"}}
_ACCOUNTS_FILE = _RUNTIME / "accounts.json"


def _ensure() -> None:
    _RUNTIME.mkdir(parents=True, exist_ok=True)


def _check_bcrypt() -> None:
    if not _BCRYPT_OK:
        raise RuntimeError(
            "bcrypt is not installed. Run:  pip install bcrypt"
        )


class AccountsUnreadable(OSError):
    """accounts.json and its backup are both damaged. Never treated as "no accounts": that would
    let the app offer Create Account over an existing setup."""


def _write(path: Path, data: bytes) -> None:
    """Atomic (old file or new, never half of one) and plain: these are read before the vault is
    unlocked, so they can't be encrypted with it (U101 review: a power cut mid-write could lose them)."""
    from cursiv_engine.core import atomic
    atomic.write_bytes(path, data, protect=False)


def _backup() -> Path:
    return _ACCOUNTS_FILE.with_name(_ACCOUNTS_FILE.name + ".bak")


def _parse(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not all(isinstance(v, dict) and "pw_hash" in v for v in value.values()):
        raise ValueError("not an accounts file")
    return value


def _load_accounts() -> dict:
    if not _ACCOUNTS_FILE.exists():
        return {}
    try:
        return _parse(_ACCOUNTS_FILE)
    except (OSError, ValueError) as first:
        # Damaged: use the last good copy, and put it back so the next save starts from it.
        try:
            accounts = _parse(_backup())
        except (OSError, ValueError):
            raise AccountsUnreadable(f"The accounts file is damaged ({first}) and its backup can't be read. "
                                     f"Nothing was changed. Files: {_ACCOUNTS_FILE}") from first
        _write(_ACCOUNTS_FILE, json.dumps(accounts, indent=2).encode("utf-8"))
        return accounts


def _save_accounts(accounts: dict) -> None:
    """The file, then the same contents as its backup: if the file is ever damaged, the backup has
    every account (a crash between the two leaves the backup one save behind, never empty)."""
    _ensure()
    data = json.dumps(accounts, indent=2).encode("utf-8")
    _write(_ACCOUNTS_FILE, data)
    _write(_backup(), data)


# ── Public API ─────────────────────────────────────────────────────────────────

def setup_credentials(username: str, password: str) -> None:
    """
    First-run setup for the primary account. Hashes the password with
    bcrypt (rounds=12, ~250ms) and stores the hash. The original password
    is never written anywhere. Call once; overwrites any existing primary
    credentials. Additional accounts (see add_account) are unaffected.
    """
    _check_bcrypt()
    _ensure()

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
    username_hash = hashlib.sha256(username.encode("utf-8")).hexdigest()

    _write(_HASH_FILE, hashed)
    _write(_META_FILE, username_hash.encode("utf-8"))
    _write(_FLAG_FILE, username_hash.encode("utf-8"))


def add_account(username: str, password: str) -> bool:
    """
    Create an additional login on this same install -- multiple people
    (e.g. family members) can each have their own username/password
    without sharing the primary account's credentials. Returns False if
    the username is already taken (by the primary account or another
    added one); True on success. Shares the same underlying app data
    (strands, API keys, etc.) as every other account on this install --
    this is multiple logins, not isolated per-user data.
    """
    _check_bcrypt()
    _ensure()

    username_hash = hashlib.sha256(username.encode("utf-8")).hexdigest()
    if username_exists(username):
        return False

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
    accounts = _load_accounts()
    accounts[username_hash] = {
        "pw_hash": base64.b64encode(hashed).decode("ascii"),
        "created": datetime.now(timezone.utc).isoformat(),
    }
    _save_accounts(accounts)
    return True


def verify_credentials(username: str, password: str) -> bool:
    """
    Login verification. Hashes the provided password and compares against the
    stored hash using bcrypt's constant-time comparison. Returns True on success.
    The original password is never stored or reconstructed anywhere. Checks
    the primary account first, then any additional accounts.
    """
    _check_bcrypt()
    username_hash = hashlib.sha256(username.encode("utf-8")).hexdigest()

    if _META_FILE.exists() and _HASH_FILE.exists():
        stored_user_hash = _META_FILE.read_text(encoding="utf-8").strip()
        if hmac.compare_digest(username_hash, stored_user_hash):
            stored_hash = _HASH_FILE.read_bytes()
            try:
                return bcrypt.checkpw(password.encode("utf-8"), stored_hash)
            except Exception:
                return False

    accounts = _load_accounts()
    entry = accounts.get(username_hash)
    if entry:
        try:
            stored_hash = base64.b64decode(entry["pw_hash"])
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash)
        except Exception:
            return False

    return False


def is_setup_complete() -> bool:
    """True if any credentials (primary or additional) have been configured. A damaged accounts file
    still counts: offering Create Account then would replace someone's existing setup."""
    if _FLAG_FILE.exists():
        return True
    try:
        return bool(_load_accounts())
    except AccountsUnreadable:
        return True


def username_exists(username: str) -> bool:
    """Return True if the username matches the primary account or any additional one."""
    username_hash = hashlib.sha256(username.encode("utf-8")).hexdigest()
    if username_hash in _load_accounts():
        return True
    if not _META_FILE.exists():
        return False
    try:
        stored = _META_FILE.read_text(encoding="utf-8").strip()
        candidate = hashlib.sha256(username.encode("utf-8")).hexdigest()
        return hmac.compare_digest(candidate, stored)
    except Exception:
        return False


def reset_password(new_password: str, username: str | None = None) -> None:
    """Replace one account's password after its own security questions were answered.
    username: the account to change (the primary when None, for older callers). Raises
    ValueError if there's no such account. Never touches any other account."""
    _check_bcrypt()
    _ensure()
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt(rounds=12))
    if username is None or is_primary(username):
        if username is None and not _primary_hash():
            raise ValueError("There's no account to reset.")
        _write(_HASH_FILE, hashed)
        return
    accounts = _load_accounts()
    key = _uhash(username)
    if key not in accounts:
        raise ValueError("There's no account with that username.")
    accounts[key]["pw_hash"] = base64.b64encode(hashed).decode("ascii")
    _save_accounts(accounts)


def reset_credentials() -> None:
    """Delete all stored credential files, returning the app to first-run state."""
    left = []
    for f in (_HASH_FILE, _META_FILE, _FLAG_FILE, _ACCOUNTS_FILE, _backup()):   # the backup too: no old accounts back
        try:
            f.unlink(missing_ok=True)
        except OSError as exc:
            left.append(f"{f.name} ({exc.strerror or exc})")
    if left:
        # U103: a locked file used to be skipped silently, so a reset could leave a login behind.
        raise OSError("Some login files could not be removed: " + ", ".join(left)
                      + ". Close other Cursiv windows and try again.")


def _uhash(username: str) -> str:
    return hashlib.sha256(username.encode("utf-8")).hexdigest()


def _primary_hash() -> str:
    """SHA-256 of the primary username, or "" when there is no primary account."""
    if not (_META_FILE.exists() and _HASH_FILE.exists()):
        return ""
    try:
        return _META_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def account_count() -> int:
    """How many logins exist on this install (primary plus additional)."""
    primary = _primary_hash()
    others = [h for h in _load_accounts() if h != primary]
    return (1 if primary else 0) + len(others)


def is_primary(username: str) -> bool:
    primary = _primary_hash()
    return bool(primary) and hmac.compare_digest(_uhash(username), primary)


def remove_account(username: str) -> bool:
    """
    Remove one login. Returns False if no such account exists. Never removes
    the last account (raises ValueError -- use start_over for that), so the
    app always has someone who can sign in. Removing the primary account
    promotes the oldest additional account to primary. The removed person's
    security questions go with them (each account has its own); left in place
    they could reset someone else's password. App data is untouched.
    """
    if not username_exists(username):
        return False
    if account_count() <= 1:
        raise ValueError("This is the only account. Use Start over to replace it.")

    target = _uhash(username)
    accounts = _load_accounts()
    from cursiv_engine.guardian.security_questions import clear_security_questions
    # The removed person's questions go with them (before any promotion: a set saved before
    # per-account questions is read as the current primary's).
    clear_security_questions(account_hash=target)
    if not is_primary(username):
        accounts.pop(target, None)
        _save_accounts(accounts)
        return True

    # Promote the oldest additional account. Write the new primary before
    # removing it from accounts.json, so an interruption leaves a duplicate
    # login, never none.
    heir = min((h for h in accounts if h != target),
               key=lambda h: accounts[h].get("created", ""))
    _ensure()
    _write(_HASH_FILE, base64.b64decode(accounts[heir]["pw_hash"]))
    _write(_META_FILE, heir.encode("utf-8"))
    _write(_FLAG_FILE, heir.encode("utf-8"))
    accounts.pop(heir, None)
    accounts.pop(target, None)
    _save_accounts(accounts)
    return True


def remove_with_password(username: str, signed_in: str, password: str) -> None:
    """
    Settings' Remove: the signed-in person proves it's them with their
    password, then names the account to remove (which may be their own).
    Raises ValueError with a sentence to show when anything is wrong.
    """
    if not (signed_in and password and verify_credentials(signed_in, password)):
        raise ValueError("Your password is not right.")
    if not username or not username_exists(username):
        raise ValueError("There's no account with that username (usernames are case-sensitive).")
    remove_account(username)


def start_over(signed_in: str, password: str) -> None:
    """
    Remove every login and the security questions after the signed-in
    person confirms their password. Memories, notebook, documents and saved
    keys stay. The caller must close the app right after: the next start
    shows Create Account.
    """
    if not (signed_in and password and verify_credentials(signed_in, password)):
        raise ValueError("Your password is not right.")
    reset_credentials()
    from cursiv_engine.guardian.security_questions import clear_security_questions
    clear_security_questions()


def fragment_status() -> dict[str, bool]:
    """Diagnostic: which credential files are present. No password data exposed."""
    return {
        "hash_file":  _HASH_FILE.exists(),
        "meta_file":  _META_FILE.exists(),
        "setup_flag": _FLAG_FILE.exists(),
        "bcrypt_ok":  _BCRYPT_OK,
    }
