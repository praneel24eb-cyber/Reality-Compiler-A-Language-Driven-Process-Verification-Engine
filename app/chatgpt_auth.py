"""Local ChatGPT OAuth with user-protected persistence and rotating refresh tokens."""

import base64
import hashlib
import json
import os
import secrets
import threading
import time
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

import httpx
import jwt

from app.llm import ExtractionError
from app.session_store import SessionStore

ISSUER = "https://auth.openai.com"
TOKEN_URL = ISSUER + "/api/accounts/oauth/token"
RESOURCE = "https://api.openai.com/v1"
CALLBACK = "http://127.0.0.1:8000/auth/callback"
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"


class ChatGPTConnection:
    """One local account, one-time browser-bound transactions, no token exposure."""

    def __init__(self, registration: Path | None = None):
        registration = registration or Path(os.getenv("CHATGPT_REGISTRATION_PATH", ".local/chatgpt-registration.json"))
        self.registration = registration
        self.lock = threading.RLock()
        self.pending: dict[str, dict] = {}
        self.credentials: dict = {}
        self.model: str | None = None
        self.catalog: list[dict] = []
        self.store = SessionStore(registration.with_suffix(".session"))
        self.persisted = False
        self.storage_error: str | None = None
        self.notice: str | None = None
        saved = self.store.load()
        if (saved and saved.get("client_id") == self._registration().get("client_id")
                and isinstance(saved.get("access_token"), str)
                and isinstance(saved.get("expires"), (int, float))):
            self.credentials = saved
            self.persisted = True

    def _persist(self) -> None:
        try:
            self.store.save(self.credentials)
            self.persisted = self.store.enabled
            self.storage_error = None
        except OSError:
            self.persisted = False
            self.storage_error = "Sign-in is active, but Windows could not save it for restart."

    def _registration(self) -> dict:
        if self.registration.exists():
            return json.loads(self.registration.read_text(encoding="utf-8"))
        record = {"host": "urn:uuid:" + str(uuid4())}
        self._save(record)
        return record

    def _save(self, record: dict) -> None:
        self.registration.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.registration.with_suffix(".tmp")
        temporary.write_text(json.dumps(record), encoding="utf-8")
        temporary.replace(self.registration)

    def start(self, registration_id: str | None = None) -> tuple[str, str]:
        """Return the authorization URL and browser-bound opaque transaction cookie."""
        with self.lock:
            stored = self._registration()
            profiles = stored.get("profiles", [])
            if stored.get("client_id"):
                profiles = [
                    {k: stored[k] for k in ("client_id", "subject", "email", "model") if k in stored},
                    *profiles,
                ]
            if registration_id == "new":
                record = {"host": stored["host"]}
            elif registration_id:
                profile = next((p for p in profiles if p.get("client_id") == registration_id), None)
                if profile is None:
                    raise ValueError("Saved ChatGPT registration not found")
                record = {"host": stored["host"], **profile}
            else:
                record = stored
            state, nonce, verifier, cookie = [secrets.token_urlsafe(32) for _ in range(4)]
            self.pending = {k: v for k, v in self.pending.items() if v["expires"] > time.time()}
            if len(self.pending) >= 10:
                raise ValueError("Too many pending sign-in attempts")
            client_id = record.get("client_id", "dynamic_agent_client")
            self.pending[cookie] = {
                "state": state,
                "nonce": nonce,
                "verifier": verifier,
                "expires": time.time() + 600,
                "client_id": client_id,
                "record": record,
            }
            params = {
                "client_id": client_id,
                "ext_agent_host_id": record["host"],
                "response_type": "code",
                "redirect_uri": CALLBACK,
                "scope": SCOPES,
                "resource": RESOURCE,
                "state": state,
                "nonce": nonce,
                "code_challenge_method": "S256",
                "code_challenge": base64.urlsafe_b64encode(
                    hashlib.sha256(verifier.encode()).digest()
                )
                .decode()
                .rstrip("="),
            }
            if client_id == "dynamic_agent_client":
                params["agent_name_hint"] = "Reality Compiler"
            return ISSUER + "/api/accounts/authorize?" + urlencode(params), cookie

    def finish(self, cookie: str, params: dict[str, str]) -> None:
        """Consume the attempt and validate signature, identity, scope and nonce."""
        with self.lock:
            pending = self.pending.pop(cookie, None)
        if (
            not pending
            or pending["expires"] <= time.time()
            or not secrets.compare_digest(pending["state"], params.get("state", ""))
        ):
            raise ValueError("Sign-in attempt expired or could not be verified. Try again.")
        if params.get("error") or not params.get("code"):
            raise ValueError("ChatGPT sign-in was not authorized. Try again when ready.")
        issued = params.get("client_id", pending["client_id"])
        if not issued.startswith("oaiapp_") or (
            pending["client_id"] != "dynamic_agent_client" and issued != pending["client_id"]
        ):
            raise ValueError("ChatGPT returned an invalid client registration")
        record = {**pending["record"], "client_id": issued}
        try:
            with httpx.Client(timeout=30, follow_redirects=False) as client:
                response = client.post(
                    TOKEN_URL,
                    data={
                        "grant_type": "authorization_code",
                        "client_id": issued,
                        "code": params["code"],
                        "code_verifier": pending["verifier"],
                        "redirect_uri": CALLBACK,
                        "resource": RESOURCE,
                    },
                )
                response.raise_for_status()
                tokens = response.json()
            token = tokens["id_token"]
            signing_key = jwt.PyJWKClient(
                ISSUER + "/.well-known/jwks.json", timeout=15
            ).get_signing_key_from_jwt(token)
            identity = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=issued,
                issuer=ISSUER,
                leeway=5,
                options={"require": ["sub", "exp", "iat", "nonce"]},
            )
            if not secrets.compare_digest(str(identity["nonce"]), pending["nonce"]):
                raise ValueError("Nonce mismatch")
            if not identity["sub"] or (
                record.get("subject") and record["subject"] != identity["sub"]
            ):
                raise ValueError("Account mismatch")
            if not {"resource.invoke", "chatgpt.tokens.use.direct"} <= set(
                tokens.get("scope", "").split()
            ):
                raise ValueError("ChatGPT plan permission was not granted")
            if not tokens.get("access_token") or tokens.get("token_type", "").lower() != "bearer":
                raise ValueError("Missing access token")
            credentials = {
                "access_token": tokens["access_token"],
                "expires": time.time() + int(tokens["expires_in"]),
                "email": identity.get("email", "Connected account"),
                "client_id": issued,
                "refresh_token": tokens.get("refresh_token"),
            }
            with self.lock:
                previous = self._registration()
                profiles = previous.get("profiles", [])
                if previous.get("client_id") and previous["client_id"] != issued:
                    profiles = [
                        {
                            k: previous[k]
                            for k in ("client_id", "subject", "email", "model")
                            if k in previous
                        },
                        *profiles,
                    ]
                profiles = [p for p in profiles if p.get("client_id") != issued]
                self._save(
                    {
                        **record,
                        "subject": identity["sub"],
                        "email": identity.get("email"),
                        "profiles": profiles,
                    }
                )
                self.credentials = credentials
                self.catalog = []
                self.model = None
                try:
                    with self.store.locked():
                        self._persist()
                except OSError:
                    self.storage_error = "Signed in, but encrypted session storage is unavailable."
        except (httpx.HTTPError, jwt.PyJWTError, KeyError, TypeError, ValueError):
            raise ValueError(
                "Could not validate ChatGPT sign-in. Check account eligibility and retry."
            ) from None

    def access_token(self) -> str:
        """Refresh expired access once, serializing replacement of rotating tokens."""
        with self.lock:
            if self.credentials and self.credentials["expires"] <= time.time() + 60 and self.credentials.get("refresh_token"):
                with self.store.locked():
                    if self.persisted:
                        saved = self.store.load()
                        if not saved or saved.get("client_id") != self.credentials.get("client_id"):
                            self.credentials = {}
                        else:
                            self.credentials = saved
                    if self.credentials and self.credentials["expires"] <= time.time() + 60:
                        self._refresh()
            if not self.credentials or self.credentials["expires"] <= time.time() + 30:
                raise ExtractionError(
                    "Connect ChatGPT again in ChatGPT Connection; the session is missing or expired.",
                    code="connection_required", status_code=401,
                )
            return str(self.credentials["access_token"])

    def _refresh(self) -> None:
        try:
            with httpx.Client(timeout=30, follow_redirects=False) as client:
                response = client.post(TOKEN_URL, data={
                    "grant_type": "refresh_token", "client_id": self.credentials["client_id"],
                    "refresh_token": self.credentials["refresh_token"], "resource": RESOURCE,
                })
            if response.status_code in {400, 401, 403}:
                self.credentials = {}
                self.store.clear()
                self.persisted = False
                raise ExtractionError("ChatGPT session renewal was rejected. Reconnect in ChatGPT Connection.", code="connection_required", status_code=401)
            response.raise_for_status()
            tokens = response.json()
            if not tokens.get("access_token") or not tokens.get("refresh_token") or tokens.get("token_type", "").lower() != "bearer":
                raise ValueError("Incomplete refresh response")
            lifetime = int(tokens["expires_in"])
            if lifetime <= 60:
                raise ValueError("Invalid refresh lifetime")
            self.credentials = {**self.credentials, "access_token": tokens["access_token"],
                                "refresh_token": tokens["refresh_token"], "expires": time.time() + lifetime}
            self._persist()
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise ExtractionError("Could not renew ChatGPT access. Check connectivity and retry.", code="refresh_unavailable", status_code=503) from None

    def status(self) -> dict:
        """Return only safe connection metadata."""
        with self.lock:
            if self.credentials.get("refresh_token") and self.credentials["expires"] <= time.time() + 60:
                try:
                    self.access_token()
                except ExtractionError:
                    pass
            connected = bool(self.credentials and self.credentials["expires"] > time.time() + 30)
            record = self._registration()
            profiles = record.get("profiles", [])
            if record.get("client_id"):
                profiles = [record, *profiles]
            return {
                "connected": connected,
                "account": self.credentials.get("email") if connected else None,
                "model": self.model,
                "ready": connected and self.model is not None,
                "models": self.catalog,
                "session_persistent": self.persisted,
                "storage_supported": self.store.enabled,
                "storage_error": self.storage_error,
                "notice": self.notice,
                "registrations": [
                    {
                        "id": p["client_id"],
                        "label": p.get("email") or "Saved account",
                        "workspace_hint": p["client_id"][-8:],
                    }
                    for p in profiles
                    if p.get("client_id")
                ],
            }

    def models(self) -> list[dict]:
        """Fetch the account-specific model catalog without guessing identifiers."""
        # Keep account switches and disconnects from racing a catalog request.
        with self.lock:
            return self._load_models()

    def _load_models(self) -> list[dict]:
        try:
            response = httpx.get(
                RESOURCE + "/models",
                headers={"Authorization": "Bearer " + self.access_token()},
                timeout=30,
            )
            response.raise_for_status()
            catalog = [
                {"slug": m["slug"], "display_name": m["display_name"]}
                for m in response.json()["models"]
                if m.get("visibility") == "list"
            ]
            with self.lock:
                self.catalog = catalog
                if self.model not in {m["slug"] for m in catalog}:
                    preferred = self._registration().get("model")
                    self.model = next(
                        (m["slug"] for m in catalog if m["slug"] == preferred),
                        catalog[0]["slug"] if catalog else None,
                    )
            return catalog
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise ExtractionError("Unable to load models for this ChatGPT account") from None

    def select(self, slug: str) -> None:
        """Only permit models advertised for this account."""
        with self.lock:
            self.access_token()
            if slug not in {m["slug"] for m in self.catalog}:
                raise ValueError("Choose an available ChatGPT model")
            self._save({**self._registration(), "model": slug})
            self.model = slug

    def request_credentials(self) -> tuple[str, str]:
        """Resolve an advertised model and token for the same connected account."""
        with self.lock:
            self.access_token()
            if not self.model:
                self.models()
            if not self.model:
                raise ExtractionError(
                    "No models are available for this ChatGPT account. Check ChatGPT Connection.",
                    code="model_unavailable", status_code=409,
                )
            return self.access_token(), self.model

    def disconnect(self) -> None:
        """Attempt revocation, then forget local credentials even if the network is down."""
        with self.lock:
            revoked = not bool(self.credentials.get("refresh_token"))
            if not revoked:
                for _ in range(2):
                    try:
                        with httpx.Client(timeout=10, follow_redirects=False) as client:
                            discovery = client.get(ISSUER + "/.well-known/openid-configuration")
                            discovery.raise_for_status()
                            endpoint = discovery.json()["revocation_endpoint"]
                            if not isinstance(endpoint, str) or not endpoint.startswith(ISSUER + "/"):
                                raise ValueError("Invalid revocation endpoint")
                            response = client.post(endpoint, data={
                                "token": self.credentials["refresh_token"],
                                "token_type_hint": "refresh_token", "client_id": self.credentials["client_id"],
                            })
                            revoked = response.status_code == 200
                        if revoked:
                            break
                    except (httpx.HTTPError, ValueError, KeyError, TypeError):
                        pass
            with self.store.locked():
                self.store.clear()
            self.persisted = False
            self.credentials = {}
            self.catalog = []
            self.model = None
            self.pending = {}
            self.notice = "Signed out and cleared this device's session." if revoked else (
                "Signed out locally. Remote revocation could not be confirmed; disconnect the app in ChatGPT settings."
            )
