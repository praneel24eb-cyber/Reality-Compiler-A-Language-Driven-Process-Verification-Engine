import httpx
import pytest

from app.llm import ExtractionError, HostedClient
from app.preprocessing import sentences


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"choices": [{"finish_reason": "stop", "message": {"content": "not json"}}]},
        {"choices": [{"finish_reason": "stop", "message": {"refusal": "refused"}}]},
        {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
    ],
)
def test_invalid_provider_output(monkeypatch, body):
    monkeypatch.setenv("LLM_API_KEY", "test-secret")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    real_client = httpx.Client
    monkeypatch.setattr("app.llm.httpx.Client", lambda **kwargs: real_client(transport=transport))
    with pytest.raises(ExtractionError):
        HostedClient().extract(sentences("Example."))


def test_transient_retry(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-secret")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(503)

    real_client = httpx.Client
    transport = httpx.MockTransport(respond)
    monkeypatch.setattr("app.llm.httpx.Client", lambda **kwargs: real_client(transport=transport))
    monkeypatch.setattr("app.llm.time.sleep", lambda seconds: None)
    with pytest.raises(ExtractionError):
        HostedClient().extract(sentences("Example."))
    assert len(calls) == 3
