"""Explicit synthetic browser fixture; never loaded by the production application."""

import streamlit as st

from ui.canvas import board_component
from ui.theme import apply_theme

st.set_page_config(layout="wide")
apply_theme()
st.title("AI Canvas")
st.caption("Browser acceptance fixture · Synthetic procedure · No account or saved data used")
board = st.session_state.setdefault(
    "fixture",
    {
        "messages": [
            {"role": "assistant", "content": "Synthetic rendering fixture, not live AI output."}
        ],
        "layout": {},
        "error": "",
        "visuals": [
            {
                "id": "workflow",
                "kind": "workflow",
                "title": "Review flow",
                "note": "Synthetic test workflow",
                "nodes": [
                    {"id": "start", "label": "Receive", "details": {"kind": "start", "actor": "Clerk", "source_passages": ["The clerk receives the request."]}},
                    {"id": "review", "label": "Review", "details": {"kind": "normal", "actor": "Manager"}},
                ],
                "edges": [
                    {"id": "a", "source": "start", "target": "review", "label": "submit"},
                    {"id": "b", "source": "start", "target": "review", "label": "resubmit"},
                    {"id": "c", "source": "review", "target": "review", "label": "retry"},
                ],
            },
            {
                "id": "mindmap",
                "kind": "mindmap",
                "title": "Process concepts",
                "note": "Synthetic conceptual map",
                "nodes": [
                    {"id": "root", "label": "Procurement"},
                    {"id": "people", "label": "People"},
                    {"id": "records", "label": "Records"},
                ],
                "edges": [
                    {"id": "d", "source": "root", "target": "people", "label": ""},
                    {"id": "e", "source": "root", "target": "records", "label": ""},
                ],
            },
        ],
    },
)


def save_layout():
    board["layout"] = st.session_state["fixture_component"].get("layout", {})


result = board_component(
    data=board,
    key="fixture_component",
    on_layout_change=save_layout,
    on_submit_change=lambda: None,
    on_remove_change=lambda: None,
)
if result.remove:
    board["visuals"] = [v for v in board["visuals"] if v["id"] != result.remove]
    st.rerun()
if result.submit and result.submit["id"] != board.get("last_event"):
    board["last_event"] = result.submit["id"]
    board["messages"].append({"role": "user", "content": result.submit["message"]})
    board["messages"].append({"role": "assistant", "content": "The clerk receives the request, then the manager reviews it."})
    st.rerun()
