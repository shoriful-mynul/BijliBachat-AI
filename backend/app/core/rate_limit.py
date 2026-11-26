"""In-process limit for expensive file checks.

A limit of 0 disables the check. This process does not share counters with
other machines, so it is not a distributed production rate limiter. Ordinary
tests stay under the default of 60 requests a minute from one client.
"""

from time import monotonic

_WINDOW_SECONDS = 60
_MAX_KEYS = 4096


def client_address(peer: str | None, forwarded: str | None, trusted_proxies: frozenset[str]) -> str:
    """Return the caller address. A forwarding header counts only from a trusted peer."""
    peer_address = (peer or "local").strip() or "local"
    if peer_address not in trusted_proxies:
        return peer_address
    chain = [item.strip() for item in (forwarded or "").split(",") if item.strip()]
    for address in reversed(chain):
        if address not in trusted_proxies:
            return address
    return peer_address


class ExtractRateLimiter:
    def __init__(self, limit_per_minute: int, max_keys: int = _MAX_KEYS) -> None:
        self.limit = limit_per_minute
        self.max_keys = max_keys
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        if self.limit <= 0:
            return True
        moment = monotonic() if now is None else now
        self._drop_stale(moment)
        recent = [stamp for stamp in self._hits.get(key, []) if moment - stamp < _WINDOW_SECONDS]
        if key not in self._hits and len(self._hits) >= self.max_keys:
            return False
        if len(recent) >= self.limit:
            self._hits[key] = recent
            return False
        recent.append(moment)
        self._hits[key] = recent
        return True

    def _drop_stale(self, moment: float) -> None:
        stale = [
            address
            for address, stamps in self._hits.items()
            if not stamps or moment - stamps[-1] >= _WINDOW_SECONDS
        ]
        for address in stale:
            del self._hits[address]
