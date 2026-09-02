"""Small HTTP helper with timeouts, a project User-Agent, and request spacing."""

from __future__ import annotations

import time
from typing import Any, Callable, Mapping, Optional

import requests

DEFAULT_USER_AGENT = (
    "Job-scrapping/1.0 "
    "(+https://github.com/antonypaulson/Job-scrapping; "
    "educational research; contact via GitHub issues)"
)
DEFAULT_TIMEOUT = 20.0
DEFAULT_MIN_INTERVAL = 2.0
MAX_RETRIES = 2


class FetchError(RuntimeError):
    """Raised when a public job API cannot be fetched safely."""


class RespectfulClient:
    """GET JSON from public APIs without hammering them.

    Spacing is enforced between calls. 429 responses wait for Retry-After
    at most once, then fail instead of looping.
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = DEFAULT_TIMEOUT,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        sleeper: Callable[[float], None] = time.sleep,
        session: Optional[requests.Session] = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if min_interval < 0:
            raise ValueError("min_interval cannot be negative")
        self.user_agent = user_agent
        self.timeout = timeout
        self.min_interval = min_interval
        self._sleep = sleeper
        self._session = session or requests.Session()
        self._last_request_at = 0.0

    def get_json(
        self,
        url: str,
        params: Optional[Mapping[str, Any]] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        last_error: Optional[Exception] = None
        for attempt in range(MAX_RETRIES + 1):
            self._throttle()
            try:
                response = self._session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
            except requests.Timeout as exc:
                last_error = FetchError(f"Timed out after {self.timeout}s requesting {url}")
                if attempt >= MAX_RETRIES:
                    raise last_error from exc
                self._sleep(self.min_interval * (attempt + 1))
                continue
            except requests.RequestException as exc:
                raise FetchError(f"Request failed for {url}: {exc}") from exc

            if response.status_code == 429:
                wait_s = _retry_after_seconds(response.headers.get("Retry-After"), default=30.0)
                if attempt >= MAX_RETRIES:
                    raise FetchError(
                        f"Rate limited by {url} (HTTP 429). Wait at least {wait_s:.0f}s and retry."
                    )
                self._sleep(min(wait_s, 60.0))
                continue

            if not response.ok:
                raise FetchError(
                    f"HTTP {response.status_code} from {url}: {response.text[:200]}"
                )

            try:
                return response.json()
            except ValueError as exc:
                raise FetchError(f"Invalid JSON from {url}") from exc

        raise FetchError(f"Request failed for {url}: {last_error}")

    def _throttle(self) -> None:
        if self._last_request_at <= 0:
            self._last_request_at = time.monotonic()
            return
        elapsed = time.monotonic() - self._last_request_at
        wait = self.min_interval - elapsed
        if wait > 0:
            self._sleep(wait)
        self._last_request_at = time.monotonic()


def _retry_after_seconds(raw: Optional[str], default: float) -> float:
    if raw is None:
        return default
    try:
        return max(float(raw), 1.0)
    except ValueError:
        return default
