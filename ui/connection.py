"""Local ChatGPT account connection without exposing OAuth tokens to Streamlit."""

import os
from urllib.parse import urlencode

import httpx
import streamlit as st

from ui.api_errors import request_error


def connection_page() -> None:
    """Let the user authorize plan usage and select an advertised model."""
    st.title("ChatGPT connection")
    st.write(
        "Connect your ChatGPT account to power SOP analysis and canvas chat. This local mode uses your plan allowance; account eligibility and limits apply."
    )
    base = os.getenv("API_URL", "http://127.0.0.1:8000")
    try:
        status_response = httpx.get(base + "/auth/chatgpt/status", timeout=10)
        status_response.raise_for_status()
        status = status_response.json()
        if not status.get("enabled"):
            st.info("Start the backend with LLM_PROVIDER=chatgpt on 127.0.0.1:8000.")
            return
        st.link_button("Continue with ChatGPT", "http://127.0.0.1:8000/auth/chatgpt/start")
        st.link_button(
            "Use a different account or workspace",
            "http://127.0.0.1:8000/auth/chatgpt/start?registration_id=new",
        )
        registrations = status.get("registrations", [])
        if len(registrations) > 1:
            labels = {
                r["id"]: f"{r['label']} (registration …{r['workspace_hint']})"
                for r in registrations
            }
            selected_registration = st.selectbox(
                "Saved ChatGPT registration", list(labels), format_func=lambda value: labels[value]
            )
            st.link_button(
                "Continue with selected registration",
                "http://127.0.0.1:8000/auth/chatgpt/start?"
                + urlencode({"registration_id": selected_registration}),
            )
        st.caption(
            "A saved registration is bound to its original workspace. Choose a different account or workspace to register it separately; workspace access still depends on OpenAI's permissions."
        )
        st.caption(
            "Complete sign-in and review the permissions in the page that opens. On Windows, your session is encrypted for your Windows account and renewed automatically when allowed."
        )
        if st.button("Refresh connection status"):
            st.rerun()
        if not status["connected"]:
            st.info(status.get("notice") or "Not connected yet.")
            return
        if not status["models"]:
            with st.spinner("Loading your available ChatGPT models…"):
                result = httpx.post(base + "/auth/chatgpt/models", timeout=40)
                result.raise_for_status()
                status["models"] = result.json()
                status_result = httpx.get(base + "/auth/chatgpt/status", timeout=10)
                status_result.raise_for_status()
                status = status_result.json()
        st.success(f"Connected: {status['account']}")
        if status.get("session_persistent"):
            st.caption("Session protected on this device · survives backend restarts")
        elif status.get("storage_error"):
            st.warning(status["storage_error"])
        elif not status.get("storage_supported", False):
            st.caption("This environment uses a memory-only session.")
        if st.button("Load available models"):
            result = httpx.post(base + "/auth/chatgpt/models", timeout=40)
            result.raise_for_status()
            st.rerun()
        if status["models"]:
            options = {m["slug"]: m["display_name"] for m in status["models"]}
            chosen = st.selectbox(
                "ChatGPT model", list(options), format_func=lambda slug: options[slug],
                index=list(options).index(status["model"]) if status["model"] in options else 0,
            )
            if st.button("Use this model"):
                result = httpx.post(base + "/auth/chatgpt/model", json={"slug": chosen}, timeout=10)
                result.raise_for_status()
                st.rerun()
        st.write("Active model:", status["model"] or "Not selected")
        if not status["models"]:
            st.warning("No models are available for this account. Check ChatGPT permissions and usage.")
        st.link_button("Manage ChatGPT usage and permissions", "https://chatgpt.com/#settings")
        if st.button("Disconnect locally"):
            httpx.post(base + "/auth/chatgpt/disconnect", timeout=10).raise_for_status()
            st.rerun()
    except (httpx.HTTPError, ValueError) as exc:
        st.error(request_error(exc))
