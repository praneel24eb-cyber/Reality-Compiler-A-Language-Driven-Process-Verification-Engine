# Reality Compiler

Transform business procedures into traceable, verifiable workflow intelligence.

The workspace uses a forest green navigation area, neutral canvas and teal controls.
See [interface acceptance](docs/interface.md) and the
[phase-by-phase Git checkpoints](docs/git-phases.md). Implementation is currently
paused at the owner's request while the existing work is published in phase order.

The objectives and implementation are mapped in
[Objectives and methodology](docs/objectives-and-methodology.md).
Use **Workflow Builder** for goal-based Q&A, **SOP Input Studio** for document
extraction, **Workflow Explorer** for evidence review and versioned edits, and
**Evaluation & Benchmarking** to compare the two-pass pipeline with a plain-LLM baseline.
Workflow Builder saves the exact goal and answers, then displays the generated
workflow and subsequent chat on one canvas. Existing analyses keep their original
source and ledger; analyze the source again to use the upgraded pipeline.

## Dynamic AI Canvas

The default page is now a shared canvas with movable chat, workflow graph and mindmap
cards. The AI selects text, a workflow graph, a conceptual mindmap, or both diagrams
based on the question and recent conversation. No manual visualization picker is
required. Select a saved analysis for workflow questions; use the SOP Input Studio
to compile a new workflow first. General conceptual mindmaps do not require an SOP.

Drag card headers or use their arrow keys, pan the background, and use Zoom / Fit
board. Click diagram nodes or transitions to inspect details. Parallel transitions
and loops remain distinct. Diagrams can be removed individually. The underlying
saved analysis is never changed by chat. Board state is scoped to each selected
analysis and retained only during the current Streamlit session, not in the database.

The `/canvas/chat` endpoint validates the AI's presentation plan. Workflow diagrams
are built from saved process data, while AI-generated mindmaps are labeled conceptual
and validated as rooted, acyclic trees. Text is rendered as text, never executable
HTML or diagram code. Provider credentials stay in the backend. Rendering and
interaction were browser-tested with explicit synthetic fixtures; live ChatGPT API
checks and their limitations are recorded under `testing/`. This uses Streamlit's supported
[custom component API](https://docs.streamlit.io/develop/concepts/custom-components/components-v2)
and requires Streamlit 1.51 or newer.

## Local startup

Install Python 3.11, then run from this directory:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In a second activated terminal: `streamlit run ui/streamlit_app.py`.
Open http://localhost:8501; API docs are at http://localhost:8000/docs.
For local ChatGPT plan usage, open **ChatGPT Connection**, select **Continue with
ChatGPT** and complete OpenAI's sign-in and permission screens. The connection page
loads available models automatically; the first AI request also resolves a model
if needed. An explicit model choice is remembered for that registration and reused
only while still available. Otherwise, the first advertised model is selected.
Account eligibility and usage limits apply.
The callback requires the backend at `127.0.0.1:8000`. Windows sessions are encrypted
with user-bound DPAPI and refresh automatically; restarting under the same Windows
account preserves sign-in. Other operating systems currently use memory-only
ChatGPT sessions. See [recovery and session storage](docs/recovery.md). The local ChatGPT mode is not
intended for shared or remotely exposed deployment. To use an API-key provider
instead, set `LLM_PROVIDER=hosted`, `LLM_API_KEY`, and `LLM_MODEL` in the backend
environment. That provider must support Chat Completions JSON mode. `.env` is
consumed by Docker Compose; direct startup uses exported shell variables.

The SOP Input Studio accepts UTF-8 text and text-based PDFs. Select PDF pages and
review the extracted text before analysis; scanned pages, diagrams and reading
order may need manual correction. The 30,000-character analysis limit applies.
Cover and contents pages may produce no workflow transitions. Such analyses remain
available for review, with visible step/transition counts; the simulation lab offers
only operations with actual targets. Select the procedure pages and analyze them
to obtain a process suitable for transition simulations. No missing connections
are fabricated. Canvas errors explain connection, usage, and timeout failures;
the retry button preserves existing diagrams and does not duplicate the question.

Run checks with `python -m pytest -v`, `ruff check .`, `mypy app ui`, and `pip-audit`.
Tests use a supplied deterministic model and never make paid provider calls.

## Architecture and boundaries

`app/models.py` contains the workflow contracts. `preprocessing.py` retains exact
sentence spans; `llm.py` contains the provider interface and hosted adapter.
`pipeline.py` runs draft extraction, source review, reference validation, and graph
verification. It stores the first draft, source hash, and pipeline stages for audit.
Invalid review references allow one correction attempt. Exact unambiguous names
resolve to step IDs; unresolved mandatory requirements remain explicit, unverified
review findings rather than executable rules. Source-derived rules require a named
target outcome to avoid applying success-path prerequisites to rejection outcomes.
`database.py` stores immutable analyses, separate scenarios, and durable Q&A drafts.
`versions.py` creates parent-linked revisions, and `benchmark.py` compares annotated
synthetic cases. Alembic revision 0002 adds the draft table without rewriting analyses.

Schema errors (duplicates, missing references, empty evidence) reject extraction.
Valid but incomplete models produce findings. Valid evidence IDs establish links,
not semantic entailment: all extracted elements carry a human-review notice.
Unsupported-language detection is a conservative keyword heuristic, not a complete
classifier. Conditional checks find lone conditional exits; multiple branches still
require human review for exhaustiveness and exclusivity. No business rule is
inferred from a state name. A configured rule requires its protected state on every
start-to-target path; a missing target means all declared terminal states. Removing
a rule's referenced state reports an invariant violation in simulations. Reachable
cycles with no route to completion are flagged. Paths are bounded using reachability
and shortest paths; no infinite path enumeration occurs.

The extraction benchmark uses normalized state names, transition endpoints, actors,
state evidence pairs, and defect categories. Precision and recall use unique sets;
empty/empty scores 1. Gold labels never enter provider prompts. The baseline uses
one AI call; the reviewed pipeline uses two calls and deterministic verification.
Nine annotated synthetic cases live in `app/benchmark_cases.json`; ten separate verifier
fixtures live in `tests/fixtures/evaluation.json`. This small synthetic set is not a
production accuracy estimate. Exact-match scores penalize synonymous wording and
do not measure condition semantics. Reports retain predictions, latency, and failures.

## Configuration

See `.env.example`: `DATABASE_URL` defaults to local SQLite; `LLM_PROVIDER` defaults
to `chatgpt`; `LLM_API_KEY` and `LLM_MODEL` are required for `hosted` mode;
`LLM_BASE_URL` defaults to OpenAI's HTTPS API;
`API_URL` configures frontend networking. Hosted calls use 30-second per-operation
timeouts and up to three attempts only for transport failures, 429s and server errors.
`POSTGRES_PASSWORD` is required for Compose; use a long URL-safe random value.
`DOMAIN` controls the optional HTTPS proxy. No credentials belong in source control.

## Linux VPS deployment

Install Docker Engine and Compose, copy the repository, copy `.env.example` to
`.env`, set credentials and a URL-safe PostgreSQL password, and restrict `.env` to
the deployment user (`chmod 600 .env`). Then:

```sh
docker compose build
docker compose up -d db
docker compose run --rm migrate
docker compose up -d backend frontend
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8501/_stcore/health
docker compose logs --tail=100 backend frontend
docker compose restart backend frontend
```

Use an SSH tunnel to port 8501 for private access. For a **synthetic-data-only**
public demonstration, point DOMAIN DNS to the VPS, permit inbound 80/443, and run
`docker compose --profile public up -d`. Caddy provisions HTTPS and proxies Streamlit;
PostgreSQL has no published port and backend/frontend bind to loopback only.
There is no authentication, authorization, tenant isolation, or abuse quota.
Public access can consume LLM credits. Do not use confidential SOPs on a public demo.

Backup (Linux shell):
`docker compose exec -T db pg_dump -U reality -Fc reality > reality.dump`.
Copy backups off-host and test restoring them to a separate recovery database.
Restore to an empty database: `docker compose exec -T db pg_restore -U reality -d reality < reality.dump`.
Stop writers before recovery; never delete the database volume as a routine restart.
Apply migrations before starting a new release. Keep previous images for rollback;
restore a compatible database backup if schema rollback is needed.

## Current verification limits

Local execution uses the available Python 3.14; CI and images target Python 3.11.
UI logic is checked with Streamlit AppTest and canvas interactions were checked in
Chrome on desktop and mobile viewports. The live synthetic benchmark is saved in
`docs/evaluation/run-2026-11-12.json`; it does not establish general accuracy or
overall improvement over the baseline. Existing GitHub CI failed its mypy step;
diagnosis is pending. VPS deployment, Docker builds and PostgreSQL integration
remain unverified. Dependencies are bounded but not locked. Graph checks cannot
certify business compliance. See the phase checkpoints for the paused work.
