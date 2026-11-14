import logging
import time
from collections.abc import Callable

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "aml-etl-course-project/1.0"
RETRYABLE_STATUS = 429
SERVER_ERROR_FLOOR = 500


class PageFetchError(RuntimeError):
    pass


def build_http_client() -> httpx.Client:
    return httpx.Client(
        timeout=30.0,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )


class HttpPageFetcher:
    def __init__(
        self,
        client: httpx.Client,
        delay_seconds: float = 1.0,
        max_attempts: int = 4,
        backoff_seconds: float = 2.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self._delay_seconds = delay_seconds
        self._max_attempts = max_attempts
        self._backoff_seconds = backoff_seconds
        self._sleep = sleep
        self._has_requested = False

    def fetch(self, url: str) -> str:
        if self._has_requested:
            self._sleep(self._delay_seconds)
        self._has_requested = True
        failure = "no attempt made"
        for attempt in range(1, self._max_attempts + 1):
            logger.debug("GET %s (attempt %d)", url, attempt)
            try:
                response = self._client.get(url)
            except httpx.TransportError as error:
                failure = f"{type(error).__name__}: {error}"
            else:
                status = response.status_code
                if status < httpx.codes.BAD_REQUEST:
                    return response.text
                failure = f"HTTP {status}"
                if status != RETRYABLE_STATUS and status < SERVER_ERROR_FLOOR:
                    raise PageFetchError(f"Fetching {url} failed with {failure}")
            if attempt < self._max_attempts:
                self._sleep(self._backoff_seconds * 2 ** (attempt - 1))
        raise PageFetchError(
            f"Fetching {url} failed after {self._max_attempts} attempts; last error: {failure}"
        )
