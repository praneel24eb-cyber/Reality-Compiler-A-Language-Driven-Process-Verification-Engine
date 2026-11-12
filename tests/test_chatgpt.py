import json
import time
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.chatgpt_auth import CALLBACK, ChatGPTConnection
from app.chatgpt_client import ChatGPTClient, provider_error, safe_diagnostics
from app.llm import ExtractionError
from app.main import create_app
from app.models import Sentence


def test_start_and_replay_protection(tmp_path):
    auth = ChatGPTConnection(tmp_path / "registration.json")
    url, cookie = auth.start()
    query = parse_qs(urlparse(url).query)
    assert query["redirect_uri"] == [CALLBACK]
    assert query["client_id"] == ["dynamic_agent_client"]
    assert query["code_challenge_method"] == ["S256"]
    assert "verifier" not in url
    with pytest.raises(ValueError):
        auth.finish(cookie, {"state": "wrong", "code": "code"})
    assert cookie not in auth.pending
    assert not auth.status()["connected"]
    assert (
        ChatGPTConnection(auth.registration)._registration()["host"]
        == query["ext_agent_host_id"][0]
    )


def test_different_workspace_preserves_existing_registration(tmp_path):
    auth = ChatGPTConnection(tmp_path / "registration.json")
    auth._save({"host": "urn:uuid:host", "client_id": "oaiapp_original", "subject": "original"})
    url, cookie = auth.start("new")
    query = parse_qs(urlparse(url).query)
    assert query["client_id"] == ["dynamic_agent_client"]
    assert query["ext_agent_host_id"] == ["urn:uuid:host"]
    with pytest.raises(ValueError):
        auth.finish(cookie, {"state": auth.pending[cookie]["state"], "error": "access_denied"})
    assert auth._registration()["client_id"] == "oaiapp_original"
    url, _ = auth.start("oaiapp_original")
    assert parse_qs(urlparse(url).query)["client_id"] == ["oaiapp_original"]
    with pytest.raises(ValueError):
        auth.start("oaiapp_unknown")


@pytest.mark.parametrize(
    "failure",
    [None, "signature", "nonce", "issuer", "audience", "expired", "scope", "denied", "client"],
)
def test_oauth_validation(tmp_path, monkeypatch, failure):
    auth = ChatGPTConnection(tmp_path / "registration.json")
    _, cookie = auth.start()
    pending = auth.pending[cookie]
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    claims = {
        "sub": "user",
        "iss": "https://auth.openai.com",
        "aud": "oaiapp_test",
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
        "nonce": pending["nonce"],
    }
    if failure in {"nonce", "issuer", "audience"}:
        claims[{"nonce": "nonce", "issuer": "iss", "audience": "aud"}[failure]] = "wrong"
    if failure == "expired":
        claims["exp"] = int(time.time()) - 60
    signer = (
        key
        if failure != "signature"
        else rsa.generate_private_key(public_exponent=65537, key_size=2048)
    )
    encoded = jwt.encode(claims, signer, algorithm="RS256")
    body = {
        "id_token": encoded,
        "access_token": "private-access",
        "expires_in": 300,
        "token_type": "Bearer",
        "scope": "resource.invoke chatgpt.tokens.use.direct" if failure != "scope" else "openid",
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    real_client = httpx.Client
    monkeypatch.setattr(
        "app.chatgpt_auth.httpx.Client", lambda **kwargs: real_client(transport=transport)
    )
    monkeypatch.setattr(
        "app.chatgpt_auth.jwt.PyJWKClient",
        lambda *args, **kwargs: SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key=key.public_key())
        ),
    )
    params = {"state": pending["state"], "client_id": "oaiapp_test", "code": "code"}
    if failure == "denied":
        params["error"] = "access_denied"
    if failure == "client":
        params["client_id"] = "dynamic_agent_client"
    if failure:
        with pytest.raises(ValueError):
            auth.finish(cookie, params)
        assert not auth.status()["connected"]
    else:
        auth.finish(cookie, params)
        assert auth.access_token() == "private-access"
        assert "private-access" not in json.dumps(auth.status())
        assert "private-access" not in auth.registration.read_text()
        auth.disconnect()
        with pytest.raises(ExtractionError):
            auth.access_token()


@pytest.mark.parametrize(
    "terminal", ["response.completed", "response.failed", "response.incomplete", "missing"]
)
def test_stream_requires_success(monkeypatch, tmp_path, terminal):
    auth = ChatGPTConnection(tmp_path / "r.json")
    auth.credentials = {"access_token": "test", "expires": time.time() + 300}
    auth.model = "account-model"
    events = [{"type": "response.output_text.delta", "delta": '{"id":"S1","text":"Example"}'}]
    if terminal != "missing":
        events.append({"type": terminal, "response": {"status": "completed"}})

    def handle(request):
        payload = json.loads(request.content)
        assert payload["store"] is False and payload["stream"] is True
        assert str(request.url) == "https://api.openai.com/v1/responses"
        return httpx.Response(200, text="\n\n".join("data: " + json.dumps(e) for e in events))

    real = httpx.Client
    monkeypatch.setattr(
        "app.chatgpt_client.httpx.Client",
        lambda **kwargs: real(transport=httpx.MockTransport(handle)),
    )
    if terminal == "response.completed":
        assert ChatGPTClient(auth).structured("Return JSON", {}, Sentence).id == "S1"
    else:
        with pytest.raises(ExtractionError):
            ChatGPTClient(auth).structured("Return JSON", {}, Sentence)


def test_local_only_guard(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "chatgpt")
    client = TestClient(create_app(), base_url="http://127.0.0.1:8000", client=("127.0.0.1", 1234))
    assert client.get("/auth/chatgpt/status").status_code == 200
    assert (
        client.get("/auth/chatgpt/status", headers={"origin": "https://evil.example"}).status_code
        == 403
    )
    assert client.get("/auth/chatgpt/status", headers={"host": "evil.example"}).status_code == 403
    assert client.get("/auth/callback?state=bad&code=bad").status_code == 400


def test_error_diagnostics_never_exposes_arbitrary_text():
    assert safe_diagnostics(
        {"code": "subscription_sharing_usage_limit_exceeded", "param": "input"}
    ) == (" code=subscription_sharing_usage_limit_exceeded. parameter=input.")
    assert safe_diagnostics({"code": "Bearer secret", "param": "source text"}) == ""


def test_model_auto_selection_and_saved_preference(tmp_path, monkeypatch):
    auth = ChatGPTConnection(tmp_path / "r.json")
    auth.credentials = {"access_token": "private-access", "expires": time.time() + 300}
    catalog = [
        {"slug": "first", "display_name": "First", "visibility": "list"},
        {"slug": "preferred", "display_name": "Preferred", "visibility": "list"},
        {"slug": "hidden", "display_name": "Hidden", "visibility": "hidden"},
    ]
    monkeypatch.setattr(
        "app.chatgpt_auth.httpx.get",
        lambda *args, **kwargs: httpx.Response(
            200, json={"models": catalog}, request=httpx.Request("GET", "https://example.test")
        ),
    )
    assert auth.request_credentials() == ("private-access", "first")
    assert auth.status()["ready"]
    auth.select("preferred")
    auth.model = None  # A new sign-in resets runtime selection.
    assert auth.request_credentials()[1] == "preferred"
    assert "private-access" not in auth.registration.read_text()
    catalog.pop(1)  # A previously selected model is no longer available.
    auth.models()
    assert auth.model == "first"
    catalog.clear()
    auth.models()
    with pytest.raises(ExtractionError) as caught:
        auth.request_credentials()
    assert caught.value.code == "model_unavailable"


@pytest.mark.parametrize("status,code", [(401, "connection_required"), (403, "access_denied"), (429, "usage_limit"), (500, "provider_error")])
def test_actionable_provider_errors(status, code):
    error = provider_error(status, {"message": "private upstream content"})
    assert error.code == code
    assert "private upstream content" not in str(error)
    assert provider_error(None, {"code": "subscription_sharing_usage_limit_exceeded"}).status_code == 429


def test_missing_connection_returns_actionable_api_error(tmp_path, monkeypatch):
    auth = ChatGPTConnection(tmp_path / "r.json")
    monkeypatch.setattr("app.main.ChatGPTConnection", lambda: auth)
    client = TestClient(create_app(client=ChatGPTClient(auth)))
    response = client.post("/canvas/chat", json={"message": "Hello"})
    assert response.status_code == 401
    assert response.json()["code"] == "connection_required"
    assert "ChatGPT Connection" in response.json()["detail"]
