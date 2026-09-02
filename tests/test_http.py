from job_scraping.http import FetchError, RespectfulClient, _retry_after_seconds


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text="", headers=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"ok": True}
        self.text = text or "{}"
        self.headers = headers or {}
        self.ok = 200 <= status_code < 300

    def json(self):
        if self._payload == "bad":
            raise ValueError("nope")
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return self.responses.pop(0)


def test_sends_user_agent_and_timeout():
    session = FakeSession([FakeResponse(payload={"jobs": []})])
    sleeps = []
    client = RespectfulClient(
        user_agent="TestAgent/1.0",
        timeout=7,
        min_interval=0,
        sleeper=sleeps.append,
        session=session,
    )
    data = client.get_json("https://example.test/api")
    assert data == {"jobs": []}
    assert session.calls[0]["headers"]["User-Agent"] == "TestAgent/1.0"
    assert session.calls[0]["timeout"] == 7
    assert sleeps == []


def test_throttles_between_requests():
    session = FakeSession([FakeResponse(), FakeResponse()])
    sleeps = []
    client = RespectfulClient(min_interval=1.5, sleeper=sleeps.append, session=session)
    client.get_json("https://example.test/a")
    client.get_json("https://example.test/b")
    assert sleeps and sleeps[0] > 0


def test_rate_limit_then_success():
    session = FakeSession(
        [
            FakeResponse(status_code=429, headers={"Retry-After": "1"}, text="slow down"),
            FakeResponse(payload={"ok": True}),
        ]
    )
    sleeps = []
    client = RespectfulClient(min_interval=0, sleeper=sleeps.append, session=session)
    assert client.get_json("https://example.test/api") == {"ok": True}
    assert any(wait >= 1 for wait in sleeps)


def test_rate_limit_exhausted_raises():
    session = FakeSession(
        [
            FakeResponse(status_code=429, headers={"Retry-After": "2"}),
            FakeResponse(status_code=429, headers={"Retry-After": "2"}),
            FakeResponse(status_code=429, headers={"Retry-After": "2"}),
        ]
    )
    client = RespectfulClient(min_interval=0, sleeper=lambda _: None, session=session)
    try:
        client.get_json("https://example.test/api")
    except FetchError as exc:
        assert "429" in str(exc)
    else:
        raise AssertionError("expected FetchError")


def test_http_error():
    session = FakeSession([FakeResponse(status_code=500, text="boom")])
    client = RespectfulClient(min_interval=0, sleeper=lambda _: None, session=session)
    try:
        client.get_json("https://example.test/api")
    except FetchError as exc:
        assert "500" in str(exc)
    else:
        raise AssertionError("expected FetchError")


def test_retry_after_parser():
    assert _retry_after_seconds("15", 30) == 15
    assert _retry_after_seconds("nope", 30) == 30
    assert _retry_after_seconds(None, 12) == 12
