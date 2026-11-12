"""HTTP API. No public authentication: bind locally or use a private network."""

import logging
import os
from datetime import datetime
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import Field
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.benchmark import CASES, BenchmarkRequest, run_benchmark
from app.builder import DraftAnswer, NewDraft, draft_source, draft_view
from app.canvas import ChatRequest, ChatResponse, respond
from app.chatgpt_auth import ChatGPTConnection
from app.chatgpt_client import ChatGPTClient
from app.database import SavedAnalysis, SavedDraft, SavedScenario, make_engine
from app.engine import Analysis, Rule, Scenario, graph, simulate
from app.llm import ExtractionError, HostedClient, LLMClient
from app.models import Contract
from app.pipeline import compile_sop
from app.preprocessing import MAX_SOURCE
from app.versions import RevisionRequest, revise

LIMITATIONS = (
    "Structural checks are not compliance certification. Evidence references do not prove "
    "semantic entailment. AI review is advisory. Sequential and conditional workflows only; "
    "concurrency and timers are out of scope. "
    "No authentication or tenant isolation; use synthetic data for demonstrations."
)


class AnalyzeRequest(Contract):
    source: str = Field(min_length=1, max_length=MAX_SOURCE)
    rules: list[Rule] = Field(default_factory=list)


class AnalysisResponse(Contract):
    id: str
    created_at: datetime
    analysis: Analysis


class ModelSelection(Contract):
    slug: str


def create_app(client: LLMClient | None = None, engine=None) -> FastAPI:
    """Construct the API with injectable provider and database for tests."""
    api = FastAPI(title="Reality Compiler", version="2.0.0")
    db = engine if engine is not None else make_engine()
    connection = ChatGPTConnection()
    local_chatgpt = client is None and os.getenv("LLM_PROVIDER", "chatgpt") == "chatgpt"
    llm = (
        client
        if client is not None
        else (ChatGPTClient(connection) if local_chatgpt else HostedClient())
    )

    @api.middleware("http")
    async def safe_request(request: Request, call_next):
        start = perf_counter()
        if local_chatgpt:
            if (
                request.url.hostname not in {"localhost", "127.0.0.1"}
                or not request.client
                or request.client.host not in {"127.0.0.1", "::1"}
            ):
                return JSONResponse(
                    status_code=403, content={"detail": "ChatGPT mode is local-only"}
                )
            origin = request.headers.get("origin")
            if origin and origin not in {
                "http://127.0.0.1:8000",
                "http://localhost:8501",
                "http://127.0.0.1:8501",
            }:
                return JSONResponse(status_code=403, content={"detail": "Origin not allowed"})
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 1000000:
                return JSONResponse(status_code=413, content={"detail": "Request too large"})
        request._body = bytes(body)
        response = await call_next(request)
        logging.getLogger("reality.api").info(
            "%s %s %.3fs", request.method, response.status_code, perf_counter() - start
        )
        return response

    @api.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse(status_code=422, content={"detail": "Invalid request fields or values"})

    @api.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        return JSONResponse(
            status_code=503, content={"detail": "Database unavailable; check migrations"}
        )

    @api.exception_handler(ExtractionError)
    async def provider_failure(request, exc):
        return JSONResponse(
            status_code=exc.status_code, content={"detail": str(exc), "code": exc.code}
        )

    @api.exception_handler(StaleDataError)
    async def stale_draft(request, exc):
        return JSONResponse(status_code=409, content={"detail": "This draft changed in another request. Refresh and try again."})

    def get_saved(session: Session, analysis_id: str) -> SavedAnalysis:
        row = session.get(SavedAnalysis, analysis_id)
        if row is None:
            raise HTTPException(404, "Analysis not found")
        return row

    @api.get("/auth/chatgpt/status")
    def connection_status():
        return {**connection.status(), "enabled": local_chatgpt}

    @api.get("/auth/chatgpt/start")
    def start_sign_in(registration_id: str | None = None):
        if not local_chatgpt:
            raise HTTPException(409, "Start backend in local ChatGPT mode")
        try:
            url, cookie = connection.start(registration_id)
        except ValueError as exc:
            raise HTTPException(429, str(exc)) from None
        response = RedirectResponse(url)
        response.set_cookie(
            "rc_oauth", cookie, httponly=True, samesite="lax", max_age=600, path="/auth/callback"
        )
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @api.get("/auth/callback")
    def auth_callback(request: Request):
        if not local_chatgpt:
            raise HTTPException(409, "Local ChatGPT mode is disabled")
        try:
            connection.finish(request.cookies.get("rc_oauth", ""), dict(request.query_params))
            message = (
                "ChatGPT connected. Return to Reality Compiler. An available model will be "
                "selected automatically; you can change it in ChatGPT Connection."
            )
            status = 200
        except ValueError:
            message = "Sign-in could not be verified or permission was declined. Return to Connection settings and try again."
            status = 400
        response = HTMLResponse(
            f"<h1>{message}</h1><a href='http://localhost:8501/connection_page'>Return to Reality Compiler</a>",
            status_code=status,
        )
        response.delete_cookie("rc_oauth", path="/auth/callback")
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @api.post("/auth/chatgpt/models")
    def available_models():
        return connection.models()

    @api.post("/auth/chatgpt/model")
    def select_model(selection: ModelSelection):
        try:
            connection.select(selection.slug)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        return connection.status()

    @api.post("/auth/chatgpt/disconnect")
    def disconnect():
        connection.disconnect()
        return connection.status()

    @api.get("/health")
    def health():
        with Session(db) as session:
            session.execute(text("SELECT 1"))
            session.execute(select(SavedAnalysis.id).limit(1))
            session.execute(select(SavedDraft.id).limit(1))
        return {"status": "ok"}

    @api.get("/evaluation/cases")
    def evaluation_cases():
        return [{"id": c["id"], "title": c["title"]} for c in CASES]

    @api.post("/evaluation/run")
    def evaluate(request: BenchmarkRequest):
        try:
            return run_benchmark(llm, request.case_ids)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @api.get("/drafts")
    def drafts():
        with Session(db) as session:
            return [draft_view(r.id, r.snapshot) for r in session.scalars(
                select(SavedDraft).order_by(SavedDraft.created_at.desc())
            )]

    @api.post("/drafts", status_code=201)
    def new_draft(request: NewDraft):
        with Session(db) as session, session.begin():
            row = SavedDraft(snapshot={"goal": request.goal, "answers": [], "analysis_id": None})
            session.add(row)
            session.flush()
            return draft_view(row.id, row.snapshot)

    def get_draft(session, identifier):
        row = session.get(SavedDraft, identifier)
        if row is None:
            raise HTTPException(404, "Workflow draft not found")
        return row

    @api.post("/drafts/{draft_id}/answers")
    def answer_draft(draft_id: str, request: DraftAnswer):
        with Session(db) as session, session.begin():
            row = get_draft(session, draft_id)
            answers = row.snapshot["answers"]
            if request.turn < len(answers) and answers[request.turn] == request.answer:
                return draft_view(row.id, row.snapshot)
            if request.turn != len(answers) or row.snapshot.get("analysis_id"):
                raise HTTPException(409, "This question was already answered. Refresh the draft.")
            row.snapshot = {**row.snapshot, "answers": [*answers, request.answer]}
            session.flush()
            return draft_view(row.id, row.snapshot)

    @api.post("/drafts/{draft_id}/compile", response_model=AnalysisResponse)
    def compile_draft(draft_id: str):
        with Session(db) as session:
            draft = get_draft(session, draft_id)
            if draft.snapshot.get("analysis_id"):
                return retrieve(draft.snapshot["analysis_id"])
            snapshot, version = dict(draft.snapshot), draft.version
        try:
            result = compile_sop(draft_source(snapshot), llm, [])
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        result.origin = "guided"
        with Session(db) as session, session.begin():
            draft = get_draft(session, draft_id)
            if draft.version != version:
                raise HTTPException(409, "Draft changed while generating. Refresh and retry.")
            row = SavedAnalysis(snapshot=result.model_dump(mode="json"))
            session.add(row)
            session.flush()
            draft.snapshot = {**snapshot, "analysis_id": row.id}
            session.flush()
            return AnalysisResponse(id=row.id, created_at=row.created_at, analysis=result)

    @api.post("/canvas/chat", response_model=ChatResponse)
    def canvas_chat(request: ChatRequest):
        analysis = None
        if request.analysis_id:
            with Session(db) as session:
                analysis = Analysis.model_validate(get_saved(session, request.analysis_id).snapshot)
        try:
            return respond(request, llm, analysis)
        except ValueError:
            raise HTTPException(502, "Provider returned an invalid canvas response") from None

    @api.post("/analyses", response_model=AnalysisResponse, status_code=201)
    def analyze(request: AnalyzeRequest):
        try:
            result = compile_sop(request.source, llm, request.rules)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        with Session(db) as session, session.begin():
            row = SavedAnalysis(snapshot=result.model_dump(mode="json"))
            session.add(row)
            session.flush()
            return AnalysisResponse(id=row.id, created_at=row.created_at, analysis=result)

    @api.get("/analyses", response_model=list[AnalysisResponse])
    def listing():
        with Session(db) as session:
            return [
                AnalysisResponse(
                    id=row.id,
                    created_at=row.created_at,
                    analysis=Analysis.model_validate(row.snapshot),
                )
                for row in session.scalars(
                    select(SavedAnalysis).order_by(
                        SavedAnalysis.created_at.desc(), SavedAnalysis.id
                    )
                )
            ]

    @api.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
    def retrieve(analysis_id: str):
        with Session(db) as session:
            row = get_saved(session, analysis_id)
            return AnalysisResponse(
                id=row.id, created_at=row.created_at, analysis=Analysis.model_validate(row.snapshot)
            )

    @api.get("/analyses/{analysis_id}/findings")
    def findings(analysis_id: str):
        return retrieve(analysis_id).analysis.findings

    @api.post("/analyses/{analysis_id}/versions", response_model=AnalysisResponse, status_code=201)
    def create_version(analysis_id: str, request: RevisionRequest):
        with Session(db) as session, session.begin():
            original = Analysis.model_validate(get_saved(session, analysis_id).snapshot)
            try:
                result = revise(original, analysis_id, request)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from None
            row = SavedAnalysis(snapshot=result.model_dump(mode="json"))
            session.add(row)
            session.flush()
            return AnalysisResponse(id=row.id, created_at=row.created_at, analysis=result)

    @api.get("/analyses/{analysis_id}/versions", response_model=list[AnalysisResponse])
    def version_history(analysis_id: str):
        history: list[AnalysisResponse] = []
        with Session(db) as session:
            current: str | None = analysis_id
            while current and len(history) < 100:
                row = get_saved(session, current)
                analysis = Analysis.model_validate(row.snapshot)
                history.append(AnalysisResponse(id=row.id, created_at=row.created_at, analysis=analysis))
                current = analysis.parent_analysis_id
        return history

    @api.post("/analyses/{analysis_id}/scenarios", status_code=201)
    def scenario(analysis_id: str, request: Scenario):
        with Session(db) as session, session.begin():
            original = Analysis.model_validate(get_saved(session, analysis_id).snapshot)
            try:
                result = simulate(original, request)
            except ValueError:
                raise HTTPException(422, "Invalid scenario or rule references after edit") from None
            row = SavedScenario(
                analysis_id=analysis_id, definition=request.model_dump(), result=result
            )
            session.add(row)
            session.flush()
            return {"id": row.id, **result}

    @api.get("/analyses/{analysis_id}/report")
    def report(analysis_id: str):
        import networkx as nx

        saved = retrieve(analysis_id)
        with Session(db) as session:
            scenarios = [
                {"id": row.id, "definition": row.definition, "result": row.result}
                for row in session.scalars(
                    select(SavedScenario).where(SavedScenario.analysis_id == analysis_id)
                )
            ]
        return {
            **saved.model_dump(mode="json"),
            "graph": nx.node_link_data(graph(saved.analysis.process)),
            "scenarios": scenarios,
            "methodology": "Draft extraction → AI source review → evidence validation → deterministic directed multigraph checks. Manual revisions rerun evidence and graph checks.",
            "limitations": LIMITATIONS,
        }

    return api


app = create_app()
