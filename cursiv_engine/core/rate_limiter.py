"""
Smooth token rate limiter — 20,000 TPM sliding window.

Uses a 60-second sliding window. Before each API call, the caller estimates
tokens and waits if the window is full. Never hard-cuts — always delivers,
just throttled. The target is to ride smoothly near 20k, not spike past it.
"""
from __future__ import annotations

import threading
import time
from collections import deque


class TokenRateLimiter:
    TPM_TARGET = 20_000
    WINDOW_S   = 60.0

    def __init__(self, tpm_target: int = TPM_TARGET) -> None:
        self._target  = tpm_target
        self._window: deque[tuple[float, int]] = deque()  # (timestamp, tokens)
        self._lock    = threading.Lock()

    def _prune(self, now: float) -> int:
        """Remove entries older than 60s. Returns current window total. Call with lock held."""
        cutoff = now - self.WINDOW_S
        while self._window and self._window[0][0] < cutoff:
            self._window.popleft()
        return sum(t for _, t in self._window)

    def estimate_tokens(self, text: str) -> int:
        """Rough estimate: 1 token ≈ 4 chars."""
        return max(1, len(text) // 4)

    def wait_if_needed(
        self,
        estimated_tokens: int,
        on_pace: "callable[[int, int], None] | None" = None,
    ) -> None:
        """
        Block until there is budget for estimated_tokens in the current window.
        Calls on_pace(used, target) each sleep cycle when throttling, so the
        caller can display status. Adds the reservation immediately on success.
        """
        while True:
            with self._lock:
                now  = time.time()
                used = self._prune(now)
                if used + estimated_tokens <= self._target:
                    self._window.append((now, estimated_tokens))
                    return
                # How long until the oldest entry expires?
                wait_s = 0.5
                if self._window:
                    oldest_ts = self._window[0][0]
                    wait_s    = max(0.1, min((oldest_ts + self.WINDOW_S) - now, 2.0))
                current_used = used

            if on_pace:
                on_pace(current_used, self._target)
            time.sleep(wait_s)

    def record_actual(self, actual_tokens: int) -> None:
        """
        Replace the last window entry with the real token count from the API
        response. Call this after a successful API call with usage data.
        """
        with self._lock:
            if self._window:
                ts, _ = self._window[-1]
                self._window[-1] = (ts, actual_tokens)

    def current_tpm(self) -> int:
        """Return total tokens used in the last 60 seconds."""
        with self._lock:
            return self._prune(time.time())

    @property
    def target(self) -> int:
        return self._target


# Module-level singleton — import this everywhere
limiter = TokenRateLimiter()
