"""Streamlit canvas page with an isolated custom component and session-scoped boards."""

import os
from pathlib import Path

import httpx
import streamlit as st
from streamlit.components.v2 import component

from app.canvas import ChatResponse
from ui.api_errors import request_error
from ui.display import analysis_label

ASSETS = Path(__file__).parent / "canvas_assets"
board_component = component(
    "reality_canvas",
    html='<div class="canvas-root"></div>',
    css=(ASSETS / "workspace.css").read_text(encoding="utf-8"),
    js=(ASSETS / "workspace.js").read_text(encoding="utf-8"),
)


def canvas_page() -> None:
    """Keep conversation, diagrams and layout together without changing analyses."""
    st.title("AI Canvas")
    st.caption(
        "Ask a question. Graphs and mindmaps appear here automatically. Drag cards; pan the background; zoom with the controls."
    )
    base = os.getenv("API_URL", "http://127.0.0.1:8000")
    try:
        response = httpx.get(base + "/analyses", timeout=15)
        response.raise_for_status()
        analyses = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        st.error(request_error(exc))
        return
    st.markdown("[ChatGPT connection and model settings](/connection_page) · "
                "[Create a workflow with guided Q&A](/builder_page)")
    labels = {a["id"]: analysis_label(a) for a in analyses}
    selected = st.selectbox(
        "Workflow context",
        [None] + [a["id"] for a in analyses],
        format_func=lambda value: labels[value] if value else "General conversation / mindmaps",
    )
    if selected:
        process = next(a["analysis"]["process"] for a in analyses if a["id"] == selected)
        if not process["transitions"]:
            st.warning(
                "This saved analysis has no transitions. Select a workflow with transitions "
                "for process paths, or analyze pages containing the actual procedure."
            )
        with st.expander("View original SOP / query"):
            st.text(next(a["analysis"]["source"] for a in analyses if a["id"] == selected))
    boards = st.session_state.setdefault("canvas_boards", {})
    board = boards.setdefault(
        selected or "general", {"messages": [], "visuals": [], "layout": {}, "error": ""}
    )
    if st.button("Clear this board"):
        boards[selected or "general"] = {"messages": [], "visuals": [], "layout": {}, "error": ""}
        st.rerun()
    key = "board_" + (selected or "general")

    def save_layout() -> None:
        board["layout"] = st.session_state[key].get("layout", {})

    result = board_component(
        data=board,
        key=key,
        on_layout_change=save_layout,
        on_submit_change=lambda: None,
        on_remove_change=lambda: None,
    )
    if result.remove:
        board["visuals"] = [v for v in board["visuals"] if v["id"] != result.remove]
        st.rerun()
    submission = result.submit
    retry_requested = bool(
        board.get("failed_message") and st.button("Retry last question", key=key + "_retry")
    )
    if retry_requested:
        submission = {"message": board["failed_message"]}
    if submission:
        message = submission.get("message", "").strip()
        event_id = submission.get("id")
        if not message or (not retry_requested and event_id == board.get("last_event")):
            return
        if not retry_requested:
            board["last_event"] = event_id
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in board["messages"] if not m.get("failed")
        ][-12:]
        retrying = bool(
            board["messages"] and board["messages"][-1].get("failed")
            and board["messages"][-1]["content"] == message
        )
        if not retrying:
            board["messages"].append({"role": "user", "content": message})
        board["error"] = ""
        try:
            with st.spinner("Thinking and preparing your canvas…"):
                response = httpx.post(
                    base + "/canvas/chat",
                    json={
                        "message": message,
                        "history": history,
                        "analysis_id": selected,
                    },
                    timeout=120,
                )
                response.raise_for_status()
                reply = ChatResponse.model_validate(response.json()).model_dump()
            board["messages"][-1].pop("failed", None)
            board.pop("failed_message", None)
            board["messages"].append({"role": "assistant", "content": reply["answer"]})
            if selected:
                ledger = {
                    s["id"]: s["text"]
                    for s in next(
                        a["analysis"]["sentences"] for a in analyses if a["id"] == selected
                    )
                }
                for visual in reply["visuals"]:
                    for element in visual["nodes"] + visual["edges"]:
                        details = element.get("details") or {}
                        if details.get("evidence"):
                            details["source_passages"] = [
                                ledger.get(ref, "Source passage unavailable")
                                for ref in details["evidence"]
                            ]
            board["visuals"].extend(reply["visuals"])
            if reply["visuals"]:
                index = len(board["visuals"]) - len(reply["visuals"])
                # Keep chat and the new workflow side by side at a readable size.
                board["layout"]["view"] = {"x": 0, "y": -index * 680, "scale": 1}
        except (httpx.HTTPError, ValueError) as exc:
            board["messages"][-1]["failed"] = True
            board["failed_message"] = message
            board["error"] = request_error(exc) + " Your diagrams are unchanged."
        st.rerun()
