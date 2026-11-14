import httpx
import pytest

from aml_etl.rates_scraper.http_page_fetcher import (
    HttpPageFetcher,
    PageFetchError,
    build_http_client,
)


def make_fetcher(responses, sleeps):
    queue = iter(responses)
    client = httpx.Client(transport=httpx.MockTransport(lambda request: next(queue)))
    return HttpPageFetcher(client, sleep=sleeps.append)


def test_retries_server_errors_then_returns_body():
    sleeps: list[float] = []
    fetcher = make_fetcher([httpx.Response(503), httpx.Response(200, text="ok")], sleeps)
    assert fetcher.fetch("https://example.org/a") == "ok"
    assert sleeps == [2.0]


def test_retries_rate_limit_with_exponential_backoff():
    sleeps: list[float] = []
    responses = [httpx.Response(429), httpx.Response(429), httpx.Response(200, text="ok")]
    assert make_fetcher(responses, sleeps).fetch("https://example.org/a") == "ok"
    assert sleeps == [2.0, 4.0]


def test_retries_transport_errors():
    sleeps: list[float] = []
    attempts = iter([httpx.ConnectError("down"), httpx.Response(200, text="ok")])

    def handler(request: httpx.Request) -> httpx.Response:
        outcome = next(attempts)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert HttpPageFetcher(client, sleep=sleeps.append).fetch("https://example.org/a") == "ok"
    assert sleeps == [2.0]


def test_politeness_delay_between_requests():
    sleeps: list[float] = []
    fetcher = make_fetcher([httpx.Response(200, text="a"), httpx.Response(200, text="b")], sleeps)
    fetcher.fetch("https://example.org/a")
    fetcher.fetch("https://example.org/b")
    assert sleeps == [1.0]


def test_raises_page_fetch_error_after_max_attempts():
    fetcher = make_fetcher([httpx.Response(503)] * 4, [])
    with pytest.raises(PageFetchError, match=r"example.org/a"):
        fetcher.fetch("https://example.org/a")


def test_does_not_retry_404():
    sleeps: list[float] = []
    fetcher = make_fetcher([httpx.Response(404)], sleeps)
    with pytest.raises(PageFetchError):
        fetcher.fetch("https://example.org/a")
    assert sleeps == []


def test_http_client_identifies_itself():
    with build_http_client() as client:
        assert client.headers["User-Agent"] == "aml-etl-course-project/1.0"
        assert client.follow_redirects
