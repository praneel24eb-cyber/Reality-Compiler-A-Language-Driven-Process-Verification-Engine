"""Guided Q&A and generated workflows on the same canvas."""

import os

import httpx
import streamlit as st

from ui.api_errors import request_error
from ui.canvas import board_component
from ui.display import workflow_visual


def builder_page():
    st.title("Workflow Builder")
    st.caption("Describe a goal, answer five questions, and generate a traceable workflow. Unknown paths stay flagged for review.")
    base = os.getenv("API_URL", "http://127.0.0.1:8000")

    def request(path, payload=None):
        try:
            response = httpx.get(base + path, timeout=20) if payload is None else httpx.post(
                base + path, json=payload, timeout=300
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            st.error(request_error(exc))
            st.stop()

    with st.form("new_workflow_goal"):
        goal = st.text_area("What do you want this workflow to achieve?", max_chars=3000)
        if st.form_submit_button("Start guided workflow") and goal.strip():
            draft = request("/drafts", {"goal": goal})
            st.session_state["builder_selected"] = draft["id"]
            st.rerun()
    drafts = request("/drafts")
    if not drafts:
        st.info("Enter a goal to begin. Your answers will be saved as you go.")
        return
    labels = {d["id"]: d["goal"] for d in drafts}
    identifier = st.selectbox("Resume a workflow", list(labels), format_func=lambda v: labels[v], key="builder_selected")
    if identifier is None:
        return
    draft = next(d for d in drafts if d["id"] == identifier)
    st.progress(len(draft["answers"]) / 5, text=f"{len(draft['answers'])} of 5 questions answered")
    if draft["ready"] and not draft["analysis_id"] and st.button("Generate workflow from my answers"):
        with st.spinner("Extracting, reviewing source support, and verifying the workflow…"):
            request(f"/drafts/{identifier}/compile", {})
        st.rerun()
    analysis = request("/analyses/" + draft["analysis_id"])["analysis"] if draft["analysis_id"] else None
    board = st.session_state.setdefault("builder_board_" + identifier, {"layout": {}, "messages": [], "error": ""})
    key = "builder_canvas_" + identifier

    def save_layout():
        board["layout"] = st.session_state[key].get("layout", {})

    data = {
        **board,
        "input_max_length": 6000 if analysis else 4000,
        "messages": draft["messages"] + board["messages"],
        "visuals": ([workflow_visual(analysis)] if analysis and not board.get("hide_workflow") else []) + board.get("visuals", []),
    }
    result = board_component(
        data=data, key=key, on_layout_change=save_layout,
        on_submit_change=lambda: None, on_remove_change=lambda: None,
    )
    if result.remove:
        if result.remove == "saved-workflow":
            board["hide_workflow"] = True
        board["visuals"] = [v for v in board.get("visuals", []) if v["id"] != result.remove]
        st.rerun()
    if board.get("hide_workflow") and st.button("Show saved workflow again"):
        board["hide_workflow"] = False
        st.rerun()
    if result.submit and result.submit.get("id") != board.get("last_event"):
        message = result.submit.get("message", "").strip()
        if message:
            if analysis:
                reply = request("/canvas/chat", {
                    "message": message, "history": board["messages"][-12:],
                    "analysis_id": draft["analysis_id"],
                })
                board["messages"] += [{"role": "user", "content": message}, {"role": "assistant", "content": reply["answer"]}]
                board.setdefault("visuals", []).extend(reply["visuals"])
            elif not draft["ready"]:
                request(f"/drafts/{identifier}/answers", {"turn": len(draft["answers"]), "answer": message})
            else:
                board["error"] = "All questions are answered. Select Generate workflow above."
            board["last_event"] = result.submit.get("id")
            st.rerun()
    if analysis:
        st.success("Workflow saved. Review its steps and findings before using it.")
        st.page_link("http://localhost:8501/explorer", label="Edit steps and required-step rules in Workflow Explorer")
        names = {s["id"]: s["name"] for s in analysis["process"]["states"]}
        st.subheader("Steps and routes")
        st.dataframe([{
            "Step": s["name"], "Actor": s["actor"] or "Not stated",
            "Next": "; ".join((e["condition"] or e["label"] or "Next") + " → " + names[e["target"]]
                              for e in analysis["process"]["transitions"] if e["source"] == s["id"]) or "No outgoing route",
        } for s in analysis["process"]["states"]], hide_index=True)
        for finding in analysis["findings"]:
            if finding["severity"] != "info":
                st.warning(finding["message"])
