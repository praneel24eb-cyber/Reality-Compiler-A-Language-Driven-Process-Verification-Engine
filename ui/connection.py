"""Groq API key entry page — key is sent to the backend and held in memory only."""

import os

import httpx
import streamlit as st

from ui.api_errors import request_error

BASE = os.getenv("API_URL", "http://127.0.0.1:8000")


def _status() -> dict:
    r = httpx.get(BASE + "/api/groq/status", timeout=8)
    r.raise_for_status()
    return r.json()


def connection_page() -> None:
    st.title("Groq API Key")
    st.write(
        "Enter your [Groq API key](https://console.groq.com/keys) to power SOP analysis "
        "and canvas chat. The key is held in backend memory only — it is **never** written "
        "to disk, logs, or source control."
    )

    try:
        status = _status()
    except (httpx.HTTPError, ValueError) as exc:
        st.error(request_error(exc))
        return

    connected = status.get("connected", False)

    if connected:
        st.success("✓ Groq API key active — backend is ready to analyse SOPs.")
        st.write("**Active model:**", status.get("model", "—"))
        st.divider()
    else:
        st.warning("No Groq key saved yet. Paste your key below and click **Save key**.")

    # ── Model selector — persisted in session_state so switching tabs keeps it ──
    model_options_list = status.get("models", [])
    model_options = {m["id"]: m.get("label", m["id"]) for m in model_options_list}
    if not model_options:
        model_options = {"llama-3.3-70b-versatile": "Llama 3.3 70B Versatile (recommended)"}

    backend_model = status.get("model", "llama-3.3-70b-versatile")
    # Restore model choice from session_state so switching tabs doesn't reset it
    if "groq_chosen_model" not in st.session_state:
        st.session_state["groq_chosen_model"] = backend_model

    ids = list(model_options)
    cur = st.session_state["groq_chosen_model"]
    default_idx = ids.index(cur) if cur in ids else 0
    chosen_model = st.selectbox(
        "Model",
        ids,
        index=default_idx,
        format_func=lambda mid: model_options.get(mid, mid),
        key="groq_model_select",
    )
    # Save selection immediately so it survives tab switches
    st.session_state["groq_chosen_model"] = chosen_model

    # ── Key input ───────────────────────────────────────────────────────────
    # Note: password fields intentionally don't repopulate for security.
    # We show a persistent status banner above instead so the user knows if a key is active.
    with st.form("groq_key_form", clear_on_submit=False):
        api_key = st.text_input(
            "Groq API key" + (" (leave blank to keep existing key)" if connected else ""),
            type="password",
            placeholder="gsk_••••••••••••••••••••••••••••••••",
            help="Get your key at https://console.groq.com/keys — starts with gsk_",
        )
        col_save, col_clear = st.columns([2, 1])
        with col_save:
            save = st.form_submit_button("Save key", type="primary", use_container_width=True)
        with col_clear:
            clear = st.form_submit_button("Clear key", use_container_width=True)

    if save:
        key_to_send = api_key.strip()
        if not key_to_send and not connected:
            st.error("Paste your Groq API key before saving.")
        else:
            try:
                payload: dict = {"model": chosen_model}
                if key_to_send:
                    payload["api_key"] = key_to_send
                elif connected:
                    # re-use existing key; only update model — backend stores it
                    # We fetch the existing key indirectly: just don't send api_key,
                    # backend will keep whatever key it already has
                    pass
                r = httpx.post(BASE + "/api/groq/key", json=payload, timeout=15)
                r.raise_for_status()
                new_model = r.json().get("model", chosen_model)
                st.session_state["groq_chosen_model"] = new_model
                st.success(f"✓ Settings saved. Model active: **{new_model}**")
                st.rerun()
            except httpx.HTTPStatusError as exc:
                st.error(f"Backend rejected the request: {exc.response.text[:400]}")
            except (httpx.HTTPError, ValueError) as exc:
                st.error(request_error(exc))

    if clear:
        try:
            r = httpx.request("DELETE", BASE + "/api/groq/key", timeout=10)
            r.raise_for_status()
            st.session_state.pop("groq_chosen_model", None)
            st.info("Key cleared from backend memory.")
            st.rerun()
        except (httpx.HTTPError, ValueError) as exc:
            st.error(request_error(exc))

    st.divider()

    # ── Persist key via .env (optional) ─────────────────────────────────────
    st.caption(
        "**Free tier:** Groq offers a generous free rate-limit for personal projects. "
        "Recommended model: **openai/gpt-oss-120b** (or **openai/gpt-oss-20b**)."
    )
    st.caption(
        "💡 **Key is loaded automatically from `.env`:** "
        "The backend reads `LLM_API_KEY` and `LLM_MODEL` from your `.env` file on startup."
    )
