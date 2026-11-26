"""In-process limit for expensive file checks.

A limit of 0 disables the check. This is not a distributed limiter. Ordinary
tests stay under the default of 60 requests a minute from one client.
"""

from time import monotonic


class ExtractRateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self.limit = limit_per_minute
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        if self.limit <= 0:
            return True
        moment = monotonic() if now is None else now
        recent = [stamp for stamp in self._hits.get(key, []) if moment - stamp < 60]
        if len(recent) >= self.limit:
            self._hits[key] = recent
            return False
        recent.append(moment)
        self._hits[key] = recent
        return True
