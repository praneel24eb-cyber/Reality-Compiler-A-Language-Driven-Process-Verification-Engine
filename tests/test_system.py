import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base, SavedAnalysis
from app.engine import Rule, Scenario, graph, simulate, verify
from app.evaluation import precision_recall
from app.llm import ExtractionError, FakeClient, HostedClient
from app.main import create_app
from app.models import ProcessModel
from app.pipeline import compile_sop
from app.preprocessing import sentences


@pytest.fixture
def process():
    return ProcessModel.model_validate(
        {
            "process_id": "example",
            "actors": ["clerk"],
            "states": [
                {
                    "id": identifier,
                    "name": identifier,
                    "kind": kind,
                    "actor": "clerk",
                    "evidence": ["S1"],
                    "inference_reason": None,
                }
                for identifier, kind in [
                    ("start", "start"),
                    ("review", "normal"),
                    ("done", "terminal"),
                ]
            ],
            "transitions": [
                {
                    "id": identifier,
                    "source": source,
                    "target": target,
                    "label": "next",
                    "condition": None,
                    "actor": "clerk",
                    "evidence": ["S1"],
                    "inferred": False,
                    "inference_reason": None,
                }
                for identifier, source, target in [
                    ("t1", "start", "review"),
                    ("t2", "review", "done"),
                ]
            ],
        }
    )


@pytest.mark.parametrize("source", ["", "  ", "x" * 30001, "bad\x00text"])
def test_invalid_source(source):
    with pytest.raises(ValueError):
        sentences(source)


def test_ledger():
    assert [s.text for s in sentences("Dr. Smith reviews 1.5 items. Done!")] == [
        "Dr. Smith reviews 1.5 items.",
        "Done!",
    ]
    assert [s.id for s in sentences("One. Two.")] == ["S1", "S2"]


@pytest.mark.parametrize(
    "problem", ["duplicate_state", "duplicate_edge", "reference", "snake", "evidence", "inference"]
)
def test_contract(process, problem):
    data = process.model_dump()
    if problem == "duplicate_state":
        data["states"].append(data["states"][0])
    elif problem == "duplicate_edge":
        data["transitions"].append(data["transitions"][0])
    elif problem == "reference":
        data["transitions"][0]["target"] = "missing"
    elif problem == "snake":
        data["states"][0]["id"] = "Bad ID"
    elif problem == "evidence":
        data["states"][0]["evidence"] = []
    else:
        data["states"][0]["inferred"] = True
    with pytest.raises(ValidationError):
        ProcessModel.model_validate(data)


def test_graph_cycles_and_parallel(process):
    process.transitions.append(process.transitions[0].model_copy(update={"id": "parallel"}))
    process.transitions.append(
        process.transitions[0].model_copy(update={"id": "loop", "source": "review"})
    )
    g = graph(process)
    assert g.number_of_edges("start", "review") == 2
    assert not any(
        f.type == "unreachable_state" for f in verify(process, sentences("Example."), [])
    )


def test_findings_and_counterexample(process):
    process.transitions.append(
        process.transitions[0].model_copy(update={"id": "shortcut", "target": "done"})
    )
    findings = verify(process, sentences("Example."), [Rule(protected="review")])
    bypass = next(f for f in findings if f.type == "bypass")
    assert bypass.counterexample_path == ["start", "done"]
    assert graph(process).has_edge(*bypass.counterexample_path)


def test_non_destructive_scenario(process):
    original = compile_sop("Example.", FakeClient(process), [])
    before = original.model_dump()
    result = simulate(original, Scenario(operation="remove_transition", element_id="t1"))
    assert original.model_dump() == before
    assert result["lost_reachability"] == ["done", "review"]
    assert any(f["type"] == "dead_end" for f in result["new_findings"])
    with pytest.raises(ValueError):
        simulate(original, Scenario(operation="remove_state", element_id="unknown"))


def test_evidence_branch_and_actor(process):
    process.transitions[0].condition = "approved"
    process.states[0].actor = None
    process.states[0].evidence = ["S99"]
    findings = verify(process, sentences("Example."), [])
    assert {"missing_branch", "unstated_actor", "unsupported_element"} <= {f.type for f in findings}


def test_metrics():
    assert precision_recall([], []) == {"precision": 1, "recall": 1}
    assert precision_recall([1, 2], [2, 3]) == {"precision": 0.5, "recall": 0.5}


def test_unconfigured_provider(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(ExtractionError):
        HostedClient().extract(sentences("Example."))


def test_api_persistence_restart_rollback(process, tmp_path):
    url = "sqlite:///" + str(tmp_path / "test.db")
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    client = TestClient(create_app(FakeClient(process), engine))
    assert client.get("/health").status_code == 200
    assert client.post("/analyses", json={"source": " "}).status_code == 422
    response = client.post("/analyses", json={"source": "Example."})
    assert response.status_code == 201
    identifier = response.json()["id"]
    assert (
        client.post(
            f"/analyses/{identifier}/scenarios",
            json={"operation": "remove_transition", "element_id": "t1"},
        ).status_code
        == 201
    )
    assert len(client.get(f"/analyses/{identifier}/report").json()["scenarios"]) == 1
    with pytest.raises(RuntimeError), Session(engine) as session, session.begin():
        session.add(SavedAnalysis(snapshot={}))
        session.flush()
        raise RuntimeError("rollback")
    engine.dispose()
    restarted = create_engine(url)
    with Session(restarted) as session:
        assert len(list(session.scalars(select(SavedAnalysis)))) == 1
    client = TestClient(create_app(FakeClient(process), restarted))
    assert client.get(f"/analyses/{identifier}").status_code == 200
    assert client.get("/analyses/missing").status_code == 404
