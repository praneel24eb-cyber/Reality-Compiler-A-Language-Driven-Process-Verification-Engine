# Reality Compiler: Merged Specification

## Scope
In scope: sequential workflows, conditional branching, named actors, states and transitions, sentence-level evidence, explicit assumptions, graph-based verification, what-if on supported structures. Cycles are allowed, so path enumeration is always bounded.

Out of scope: parallel gateways and concurrency, timers, asynchronous events, BPMN execution, autonomous process execution, unrequested integrations.

## Pipeline
M1 Preprocessing, M2 LLM extraction, M3 Validation and gap detection, M4 Graph builder (MultiDiGraph), M5 Verification and what-if, M6 UI and report, M7 Database and API, M8 Evaluation. The LLM is used only in M2 and the M3 suggestion step. Verification is deterministic.

## Data contract (do not add or rename fields)
```text
Sentence    id, text
State       id (snake_case, unique), name, kind (start|normal|terminal), actor|None,
            evidence[] (non-empty), inferred=False, inference_reason|None
Transition  id, source, target, label, condition|None, actor|None,
            evidence[] (non-empty), inferred=False, inference_reason|None
ProcessModel process_id, actors[], states[], transitions[]
Finding     id, type, severity (info|warning|error), location|None, message,
            evidence[], counterexample_path[]|None
types: unsupported_element, assumption, missing_branch, unstated_actor,
       dead_end, unreachable_state, bypass, invariant_violation
```

Request, response, persistence and evaluation models are separate. Edge IDs for counterexamples and finding status (open, confirmed, dismissed) live outside `Finding`.

## Amendments over the original prompt
- Keep MultiDiGraph so parallel transitions stay distinct. Transition.inferred defaults to False.
- M3 adds a multi-run consistency check (n=3), where elements missing from a majority of runs become assumption findings. It also adds LLM missing-outcome suggestions, shown as info and prefixed "Suggested:", never stored as facts.
- Human review: confirm, dismiss or edit findings, with re-validation and re-verification after every edit.
- What-if also supports add_state and add_transition.
- Evaluation: at least 30 SOPs, a fixed dev/test split (test reported only with a --final flag), seeded defects, baseline A (single direct prompt), baseline B (pipeline without M3), per-source reporting, hallucination rate.
- Complete every Must item before any Should or Defer item.

## Working rules
- One phase per session. Stop after each phase with test results and wait for confirmation.
- No fabricated scores, no mocked UI metrics, no claiming deployment unless verified, no compliance claims from structural checks alone.
- Treat SOP text as untrusted input. Never log full SOP content or commit secrets.
- A valid evidence ID does not prove semantic support. Flag uncertain support for review.

## Priority tiers
| Tier | Contents |
| --- | --- |
| Must | M1 to M5, persistence and API, evaluation with baselines, six core UI pages, tests, CI with pytest and ruff |
| Should | Alembic, dashboard page, local Docker Compose, mypy on core modules, semantic-support flagging |
| Defer | VPS and HTTPS deployment, backup and restore docs, dependency scanning, production Postgres hardening |

