"""Regression coverage for the stated objectives and methodology."""

import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.builder import QUESTIONS
from app.database import Base
from app.engine import Rule, Scenario, simulate, verify
from app.llm import FakeClient
from app.main import create_app
from app.models import ProcessModel
from app.pipeline import compile_sop
from app.preprocessing import sentences


@pytest.fixture
def workflow():
    shared = {"actor": "clerk", "evidence": ["S1"], "inferred": False, "inference_reason": None}
    return ProcessModel.model_validate({
        "process_id": "test", "actors": ["clerk"],
        "states": [{"id": i, "name": n, "kind": k, **shared} for i, n, k in [
            ("receive", "Receive request", "start"), ("review", "Review request", "normal"),
            ("archive", "Archive request", "terminal"),
        ]],
        "transitions": [{"id": i, "source": a, "target": b, "condition": None, "label": "Next", **shared}
                        for i, a, b in [("t1", "receive", "review"), ("t2", "review", "archive")]],
    })


def test_exact_spans_preserve_wrapped_pdf_sentences():
    source = "  Dr. Smith reviews the\nrequest for 1.5 hours.\n\n- Archive it.\n- Notify the clerk.  "
    ledger = sentences(source)
    assert len(ledger) == 3
    assert "the\nrequest" in ledger[0].text
    assert all(source[s.start:s.end] == s.text for s in ledger)


def test_review_corrects_draft_and_extracts_source_rule(workflow):
    class Reviewer(FakeClient):
        def structured(self, prompt, data, schema):
            assert "candidate" in data and "sentences" in data
            result = self.process.model_dump()
            result["states"][1]["actor"] = None
            return schema.model_validate({
                "process": result,
                "issues": [{"category": "unstated_actor", "location": "review", "message": "Who reviews?", "evidence": ["S1"]}],
                "required_rules": [{"protected": "review", "target": "archive", "evidence": ["S1"]}],
            })
    source = "Review must occur before archiving."
    analysis = compile_sop(source, Reviewer(workflow), [])
    assert analysis.extraction_draft.states[1].actor == "clerk"
    assert analysis.process.states[1].actor is None
    assert analysis.rules[0].protected == "review"
    assert analysis.source_sha256 == hashlib.sha256(source.encode()).hexdigest()
    assert any(f.method == "llm_review" for f in analysis.findings)
    assert len(analysis.stages) == 5


def test_source_rule_requires_specific_outcome():
    from pydantic import ValidationError

    from app.pipeline import SourceRule

    with pytest.raises(ValidationError):
        SourceRule(protected="stock", target=None, evidence=["S1"])
    assert SourceRule(protected="stock", target="production", evidence=["S1"]).target == "production"


def test_review_repairs_unknown_rule_id_once(workflow):
    class Reviewer(FakeClient):
        calls = 0

        def structured(self, prompt, data, schema):
            self.calls += 1
            target = "nonexistent" if self.calls == 1 else "archive"
            return schema.model_validate({"process": self.process.model_dump(), "issues": [],
                "required_rules": [{"protected": "review", "target": target, "evidence": ["S1"]}]})
    client = Reviewer(workflow)
    result = compile_sop("Review must precede archive.", client, [])
    assert client.calls == 2
    assert "review_reference_repair" in result.stages
    assert result.rules[0].target == "archive"


def test_unresolved_rule_is_visible_and_never_executed(workflow):
    class Reviewer(FakeClient):
        def structured(self, prompt, data, schema):
            return schema.model_validate({"process": self.process.model_dump(), "issues": [],
                "required_rules": [{"protected": "missing", "target": "archive", "evidence": ["S1"]}]})
    result = compile_sop("Review before archiving.", Reviewer(workflow), [])
    assert result.rules == []
    assert any("NOT been verified" in f.message for f in result.findings)


def test_exact_rule_display_name_resolves_without_extra_call(workflow):
    from app.pipeline import ExtractionReview, resolve_rule_references

    review = ExtractionReview.model_validate({"process": workflow.model_dump(), "issues": [],
        "required_rules": [{"protected": "Review request", "target": "Archive request", "evidence": ["S1"]}]})
    resolve_rule_references(review, workflow)
    assert review.required_rules[0].protected == "review"
    assert review.required_rules[0].target == "archive"


def test_invalid_review_rolls_back_instead_of_saving(workflow, tmp_path):
    class Reviewer(FakeClient):
        def structured(self, prompt, data, schema):
            result = self.process.model_dump()
            result["states"][0]["evidence"] = ["S999"]
            return schema.model_validate({"process": result, "issues": []})
    engine = create_engine("sqlite:///" + str(tmp_path / "test.db"))
    Base.metadata.create_all(engine)
    client = TestClient(create_app(Reviewer(workflow), engine))
    assert client.post("/analyses", json={"source": "A procedure."}).status_code == 502
    assert client.get("/analyses").json() == []


def test_cycle_and_dead_end_have_real_witnesses(workflow):
    workflow.transitions[-1].target = "review"
    findings = verify(workflow, sentences("Example."), [])
    trapped = next(f for f in findings if "cycle" in f.message)
    assert trapped.counterexample_path == ["receive", "review"]
    unreachable = next(f for f in findings if f.type == "unreachable_state")
    assert unreachable.counterexample_path is None  # No path exists to exhibit.


def test_removed_required_step_reports_violation_and_bypass(workflow):
    workflow.transitions.append(workflow.transitions[0].model_copy(update={"id": "shortcut", "target": "archive"}))
    analysis = compile_sop("Example.", FakeClient(workflow), [Rule(protected="review")])
    result = simulate(analysis, Scenario(operation="remove_state", element_id="review"))
    assert any(f["type"] == "invariant_violation" for f in result["findings"])
    assert any(f["type"] == "bypass" and f["counterexample_path"] == ["receive", "archive"] for f in result["findings"])


def test_guided_draft_resume_idempotency_and_version_history(workflow, tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "test.db"))
    Base.metadata.create_all(engine)
    client = TestClient(create_app(FakeClient(workflow), engine))
    draft = client.post("/drafts", json={"goal": "Handle requests"}).json()
    path = "/drafts/" + draft["id"]
    assert client.post(path + "/compile").status_code == 422
    for i in range(len(QUESTIONS)):
        payload = {"turn": i, "answer": "User-provided answer " + str(i)}
        first = client.post(path + "/answers", json=payload)
        assert first.status_code == 200
        assert client.post(path + "/answers", json=payload).json() == first.json()
    client = TestClient(create_app(FakeClient(workflow), engine))
    assert client.get("/drafts").json()[0]["ready"]
    saved = client.post(path + "/compile").json()
    assert saved["analysis"]["origin"] == "guided"
    assert client.post(path + "/compile").json()["id"] == saved["id"]
    process = saved["analysis"]["process"]
    process["states"][1]["name"] = "Review incoming request"
    revision = client.post("/analyses/" + saved["id"] + "/versions", json={"process": process, "reason": "Clarify the review step"})
    assert revision.status_code == 201
    new = revision.json()
    assert new["analysis"]["process"]["states"][1]["inferred"]
    assert not client.get("/analyses/" + saved["id"]).json()["analysis"]["process"]["states"][1]["inferred"]
    history = client.get("/analyses/" + new["id"] + "/versions").json()
    assert [v["id"] for v in history] == [new["id"], saved["id"]]


def test_migration_retains_existing_analyses(tmp_path, monkeypatch, workflow):
    from alembic.config import Config
    from sqlalchemy import inspect
    from sqlalchemy.orm import Session

    from alembic import command
    from app.database import SavedAnalysis

    url = "sqlite:///" + str(tmp_path / "migration.db")
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "0001")
    engine = create_engine(url)
    with Session(engine) as session, session.begin():
        session.add(SavedAnalysis(snapshot=compile_sop("Example.", FakeClient(workflow), []).model_dump(mode="json")))
    command.upgrade(config, "head")
    assert "drafts" in inspect(engine).get_table_names()
    client = TestClient(create_app(FakeClient(workflow), engine))
    assert client.get("/health").status_code == 200
    assert len(client.get("/analyses").json()) == 1


def test_benchmark_keeps_gold_out_of_provider_input(workflow):
    from app.benchmark import run_benchmark

    class BenchmarkClient(FakeClient):
        def structured(self, prompt, data, schema):
            assert "states" not in data and "defects" not in data and "state_evidence" not in data
            if "candidate" in data:
                return super().structured(prompt, data, schema)
            return schema.model_validate({"process": self.process.model_dump(), "defects": []})
    report = run_benchmark(BenchmarkClient(workflow), ["sequential"])
    result = report["cases"][0]
    assert result["plain_llm"]["status"] == result["multipass_verified"]["status"] == "ok"
    # This fixture has an extra review step. The benchmark must not award perfect scores.
    assert result["plain_llm"]["metrics"]["states"]["precision"] < 1


@pytest.mark.parametrize("title", ["Workflow Builder", "Workflow Explorer", "Evaluation & Benchmarking"])
def test_new_pages_render_without_code_blocks(workflow, monkeypatch, title):
    from pathlib import Path
    from types import SimpleNamespace

    import httpx
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    from app.benchmark import CASES
    from app.builder import draft_view

    analysis = compile_sop("The clerk receives and archives a request.", FakeClient(workflow), []).model_dump(mode="json")
    saved = {"id": "saved", "created_at": "2026-11-12T10:00:00", "analysis": analysis}

    def get(url, **kwargs):
        path = url.replace("http://127.0.0.1:8000", "")
        data = {
            "/analyses": [saved], "/analyses/saved": saved, "/analyses/saved/versions": [saved],
            "/drafts": [draft_view("draft", {"goal": "Handle requests", "answers": ["A user answer"] * 5, "analysis_id": "saved"})],
            "/evaluation/cases": [{"id": c["id"], "title": c["title"]} for c in CASES],
        }[path]
        return httpx.Response(200, json=data, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", get)
    monkeypatch.setattr(httpx.Client, "get", lambda self, url, **kwargs: get(url, **kwargs))
    navigation = st.navigation

    def choose(pages):
        navigation(pages)
        return SimpleNamespace(run=next(p for p in pages if p.title == title)._page)
    monkeypatch.setattr(st, "navigation", choose)
    page = AppTest.from_file(Path("ui/streamlit_app.py").resolve()).run(timeout=30)
    assert not page.exception
    assert not page.json
