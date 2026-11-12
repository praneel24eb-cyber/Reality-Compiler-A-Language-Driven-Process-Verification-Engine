import json
import os
import time

import httpx
import pytest

from app.chatgpt_auth import ChatGPTConnection
from app.llm import ExtractionError
from app.session_store import SessionStore


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI integration")
def test_encrypted_restart_and_disconnect(tmp_path):
    path = tmp_path / "registration.json"
    first = ChatGPTConnection(path)
    first._save({"host": "test", "client_id": "oaiapp_test"})
    first.credentials = {"client_id": "oaiapp_test", "access_token": "secret-access", "expires": time.time() + 3600}
    with first.store.locked():
        first._persist()
    assert b"secret-access" not in first.store.path.read_bytes()
    restarted = ChatGPTConnection(path)
    assert restarted.access_token() == "secret-access"
    assert restarted.status()["session_persistent"]
    assert "secret-access" not in json.dumps(restarted.status())
    restarted.disconnect()
    assert not ChatGPTConnection(path).status()["connected"]


@pytest.mark.parametrize("status", [200, 400, 503])
def test_refresh_rotation_and_failure(tmp_path, monkeypatch, status):
    auth = ChatGPTConnection(tmp_path / "registration.json")
    auth.credentials = {"client_id": "oaiapp_test", "access_token": "old", "refresh_token": "old-refresh", "expires": time.time() - 1}
    calls = []

    def handle(request):
        calls.append(request)
        assert b"client_id=oaiapp_test" in request.content
        assert b"refresh_token=old-refresh" in request.content
        return httpx.Response(status, json={"access_token": "new", "refresh_token": "replacement", "token_type": "Bearer", "expires_in": 3600})
    real = httpx.Client
    monkeypatch.setattr("app.chatgpt_auth.httpx.Client", lambda **kw: real(transport=httpx.MockTransport(handle)))
    if status == 200:
        assert auth.access_token() == "new"
        assert auth.access_token() == "new"
        assert auth.credentials["refresh_token"] == "replacement"
    else:
        with pytest.raises(ExtractionError) as caught:
            auth.access_token()
        assert caught.value.status_code == (401 if status == 400 else 503)
        assert bool(auth.credentials) == (status == 503)
    assert len(calls) == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI integration")
def test_corrupt_secret_fails_closed(tmp_path):
    store = SessionStore(tmp_path / "session")
    store.path.write_bytes(b"not a valid credential blob")
    assert store.load() == {}


def test_signout_revokes_and_never_exposes_tokens(tmp_path, monkeypatch):
    auth = ChatGPTConnection(tmp_path / "r.json")
    auth.credentials = {"refresh_token": "secret-refresh", "client_id": "oaiapp_test", "expires": time.time() + 300, "access_token": "secret-access"}
    calls = []

    def handle(request):
        calls.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"revocation_endpoint": "https://auth.openai.com/revoke"})
        assert b"token=secret-refresh" in request.content
        return httpx.Response(200)
    real = httpx.Client
    monkeypatch.setattr("app.chatgpt_auth.httpx.Client", lambda **kw: real(transport=httpx.MockTransport(handle)))
    auth.disconnect()
    assert len(calls) == 2
    assert not auth.credentials
    assert "secret" not in json.dumps(auth.status())
