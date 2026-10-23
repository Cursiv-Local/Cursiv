"""OS-held cross-process lease shared by desktop startup and offline migration."""
from __future__ import annotations

import os
from pathlib import Path
from . import vault


class DataLease:
    def __init__(self, directories=None):
        self.roots = directories if directories is not None else vault.roots()
        self._streams = []

    def __enter__(self):
        try:
            for root in sorted(set(Path(p).absolute() for p in self.roots)):
                root = vault.checked(root)
                root.mkdir(parents=True, exist_ok=True)
                path = vault.checked(root / '.vault-lease')
                stream = path.open('a+b')
                self._streams.append(stream)
                if not path.stat().st_size:
                    stream.write(b'0'); stream.flush()
                stream.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.__exit__(None, None, None)
            raise vault.VaultError('Cursiv data is in use or unavailable. Close other Cursiv processes first.') from exc
        return self

    def __exit__(self, *args):
        for stream in reversed(self._streams):
            stream.close()  # OS releases the lease, including after a crash.
        self._streams.clear()
