from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest


def test_empty_canvas(monkeypatch):
    def get(self, url, **kwargs):
        return httpx.Response(200, json=[], request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.Client, "get", get)
    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: get(None, url, **kwargs))
    page = AppTest.from_file(Path(__file__).resolve().parents[1] / "ui/streamlit_app.py").run(
        timeout=30
    )
    assert not page.exception
    assert page.title[0].value == "AI Canvas"
    assert page.selectbox[0].value is None


@pytest.mark.parametrize("has_transitions", [False, True])
def test_simulation_targets_match_saved_workflow(monkeypatch, has_transitions):
    row = {
        "id": "saved", "created_at": "2026-11-12T12:00:00",
        "analysis": {
            "source": "The clerk receives and archives the request.",
            "process": {
                "states": [{"id": "start", "name": "Receive"}, {"id": "end", "name": "Archive"}],
                "transitions": [{"id": "t1", "source": "start", "target": "end", "label": "Archive"}] if has_transitions else [],
            },
        },
    }
    monkeypatch.setattr(
        httpx.Client, "get", lambda self, url, **kwargs: httpx.Response(
            200, json=[row], request=httpx.Request("GET", url)
        ),
    )
    navigation = st.navigation

    def lab_navigation(pages):
        navigation(pages)
        page = next(p for p in pages if p.title == "What-If Simulation Lab")
        return SimpleNamespace(run=page._page)

    monkeypatch.setattr(st, "navigation", lab_navigation)
    page = AppTest.from_file(Path(__file__).resolve().parents[1] / "ui/streamlit_app.py").run(timeout=30)
    assert not page.exception
    operation = next(s for s in page.selectbox if s.label == "Operation")
    if has_transitions:
        assert "Remove transition" in operation.options
        assert not page.warning
    else:
        assert operation.options == ["Remove state"]
        assert "no transitions" in page.warning[0].value
    assert not page.json


def test_api_errors_show_recovery_action():
    from ui.api_errors import request_error

    response = httpx.Response(
        401, json={"detail": "Reconnect in ChatGPT Connection."},
        request=httpx.Request("POST", "http://localhost/canvas/chat"),
    )
    with pytest.raises(httpx.HTTPStatusError) as caught:
        response.raise_for_status()
    assert request_error(caught.value) == "Reconnect in ChatGPT Connection."
    assert "timed out" in request_error(httpx.ReadTimeout("private detail"))


def test_canvas_retry_keeps_query_once_and_preserves_diagrams(monkeypatch):
    import ui.canvas

    monkeypatch.setattr(
        httpx, "get", lambda url, **kwargs: httpx.Response(
            200, json=[], request=httpx.Request("GET", url)
        ),
    )
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return httpx.Response(
            401 if len(calls) == 1 else 200,
            json={"detail": "Reconnect in ChatGPT Connection."} if len(calls) == 1
            else {"answer": "The workflow is ready.", "visuals": []},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(
        ui.canvas, "board_component", lambda **kwargs: SimpleNamespace(
            remove=None, submit={"message": "Explain my workflow", "id": "first-event"}
        ),
    )
    page = AppTest.from_file(Path(__file__).resolve().parents[1] / "ui/streamlit_app.py").run(timeout=30)
    assert not page.exception
    board = page.session_state["canvas_boards"]["general"]
    assert "Reconnect" in board["error"]
    board["visuals"] = [{"id": "existing-diagram"}]
    next(b for b in page.button if b.label == "Retry last question").click().run(timeout=30)
    assert not page.exception
    board = page.session_state["canvas_boards"]["general"]
    assert board["error"] == ""
    assert board["visuals"] == [{"id": "existing-diagram"}]
    assert [m["role"] for m in board["messages"]] == ["user", "assistant"]
    assert calls[-1]["history"] == []
