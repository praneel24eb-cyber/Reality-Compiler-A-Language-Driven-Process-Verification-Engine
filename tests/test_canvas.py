import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.canvas import CanvasPlan, ChatRequest, respond
from app.llm import ExtractionError
from app.main import create_app


class Planner:
    def __init__(self, visuals):
        self.visuals = visuals

    def structured(self, prompt, data, schema):
        return schema.model_validate(
            {
                "answer": "Here is the requested view.",
                "visuals": self.visuals,
                "title": "Topics",
                "topics": [
                    {"id": "root", "label": "Process", "parent": None},
                    {"id": "child", "label": "People", "parent": "root"},
                ],
            }
        )


@pytest.mark.parametrize("visuals", [[], ["mindmap"], ["workflow"], ["workflow", "mindmap"]])
def test_visual_routing_without_workflow(visuals):
    response = respond(ChatRequest(message="Explain this"), Planner(visuals), None)
    assert [v.kind for v in response.visuals] == [v for v in visuals if v != "workflow"]
    if "workflow" in visuals:
        assert "Select a saved analysis" in response.answer


@pytest.mark.parametrize(
    "topics",
    [
        [{"id": "x", "label": "x", "parent": "x"}],
        [{"id": "x", "label": "x", "parent": None}, {"id": "y", "label": "y", "parent": "z"}],
        [{"id": "x", "label": "x", "parent": None}, {"id": "x", "label": "y", "parent": None}],
    ],
)
def test_reject_invalid_mindmap(topics):
    with pytest.raises(ValidationError):
        CanvasPlan(answer="Answer", visuals=["mindmap"], title="Title", topics=topics)


def test_chat_api_validation_and_response():
    client = TestClient(create_app(client=Planner(["mindmap"])))
    assert client.post("/canvas/chat", json={"message": " "}).status_code == 422
    assert client.post("/canvas/chat", json={"message": "x" * 6001}).status_code == 422
    result = client.post("/canvas/chat", json={"message": "Map the concepts"})
    assert result.status_code == 200
    assert result.json()["visuals"][0]["kind"] == "mindmap"


def test_chat_error_is_not_fake_success():
    class Broken:
        def structured(self, *args):
            raise ExtractionError("Provider unavailable")

    client = TestClient(create_app(client=Broken()))
    assert client.post("/canvas/chat", json={"message": "hello"}).status_code == 502
