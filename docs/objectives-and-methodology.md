# Reality Compiler: objectives and implementation

Scope: sequential procedures and conditional branches. Parallel execution, timers,
asynchronous events, executable orchestration, and compliance certification are
outside scope. Source descriptions of these features are flagged for review.
The application is local and single-user. Visual styling remains owner-controlled.

| Objective / method | Implementation | Verification |
| --- | --- | --- |
| Natural language → states, transitions, actors, conditions | Typed ProcessModel; first-pass draft followed by a source-review pass | Contract and multi-pass regression tests; live SOP run |
| Assumptions, rejection, exception and failure gaps | Inference flags/reasons, source-review issues, conditional-exit checks | Seeded missing-rejection benchmark and verifier cases |
| Sentence traceability | Unmodified source, sentence IDs, exact character spans, source hash; final references validated before saving | Wrapped-text and invalid-reference tests |
| Dead ends, unreachable states, bypasses, invariants | Directed multigraph; reachability, required-step rules, closed-cycle checks, duplicate conditions, start/terminal constraints | Structural fixtures, real witness-path tests, required-step removal test |
| Goal-based Q&A and generated visuals | Workflow Builder asks five scope/actor/route/failure/requirement questions; saves each answer; compiles them and displays graph beside chat | Durable-draft, replay, compile-idempotency, and UI tests |
| Multi-pass structured extraction | Draft → AI review/correction → evidence validation → graph verification | Initial draft and stage metadata retained in analysis snapshots |
| What-if simulation | Copy-on-write graph edits; rerun structural checks and compare findings/reachability | Original snapshot remains unchanged; removed rule references become findings |
| Database and provenance | Immutable analysis rows, separate scenarios, durable drafts, parent version links, reasons and source fingerprints | Alembic upgrade preserves existing analyses; version ancestry tests |
| Graph review/editing | Workflow Explorer edits names, actors, conditions, connections, evidence links and required-step rules; each save creates a version | UI smoke tests and immutable-revision tests |
| Evaluation and benchmarking | Annotated seed procedures compared against a plain-LLM extraction/defect baseline using the same model | Metrics include states, transition endpoints, actors, state evidence and defect categories; reports retain predictions |
| Documentation/version control | This mapping, README, regression artifacts, Git ignore rules and GitHub CI | Python tests, Ruff, mypy; database migration check |

## Source and review guarantees

The original source is never normalized or overwritten. Sentence offsets are
zero-based Python character indices with an exclusive end. PDF hard line wraps
inside a sentence are preserved in that sentence; blank paragraphs and bullet
boundaries split passages. PDF text extraction is not OCR, and reading order may
still need correction. Old saved analyses retain their original ledger and can
lack offsets; they are not silently re-extracted.

The second AI pass corrects unsupported actor assignments, checks source links,
flags semantic gaps, and extracts required-step rules only where the source
explicitly states a mandatory requirement. Every final element and extracted rule
must cite known sentence IDs. Rules remain visible and editable by step name.
Source-derived rules require a specific target state, so a requirement for the
success path is not accidentally applied to rejection outcomes. One bounded
correction pass is allowed for invalid review references; its use is recorded in
the analysis stages. Exact unambiguous display names and preserved draft names can
resolve to actual step IDs. Requirements still lacking matching steps become
explicit “not verified” review findings and are not executed as rules. Unknown
source citations or invalid process references are rejected without saving.
Schema validity and valid citations do not establish semantic truth: AI review
findings are labeled separately from deterministic structural findings.

Cover/index material is not promoted into a fictional procedure. Empty/incomplete
models remain reviewable and cannot offer transition simulations without edges.

## Graph guarantees and limits

The graph preserves parallel transitions and loops as separate edges. A reachable
dead end or trapped cycle includes a path from a declared start. A bypass includes
a start-to-outcome path avoiding the required step. Unreachable states have no
start-path counterexample because such a path does not exist. A structural
counterexample describes a possible graph route; it does not solve arbitrary
natural-language condition predicates or prove a real-world execution is feasible.

Multiple branch conditions still need human review for exhaustiveness and mutual
exclusivity. Duplicate conditions are flagged. Semantic exception/failure gaps
depend on the source-review model and can be missed or over-reported.

## User changes and provenance

Guided drafts store the exact goal and answers before any AI generation. Replay of
an identical answer is idempotent; conflicting concurrent edits return a conflict.
Generating an already compiled draft returns the same analysis. Editing a workflow
creates a new analysis with a parent link and a reason. Changed elements are marked
as user revisions, retaining the original source for comparison. Prior AI review
warnings are carried forward where relevant and labeled for re-review; manual edits
rerun deterministic checks, not a hidden AI review.

## Evaluation interpretation

The included three extraction cases and ten structural verifier fixtures are small
synthetic seed sets, not an independently curated production benchmark. Gold data
is never sent to the provider. A plain-LLM baseline uses one call to extract and
predict defects; the reviewed method uses two calls plus graph checks. Comparisons
therefore include an additional inference cost and latency. An invalid review can
trigger one additional reference-correction call, which is recorded in its stages.

Names use normalized exact match, so equivalent wording can score as an error.
Transition scoring measures endpoints rather than full condition semantics; evidence
scoring covers states; defect scores compare categories rather than locations.
Failures remain failures in reports instead of receiving synthetic scores. A larger
independently annotated SOP set is necessary before claiming general accuracy.

Structured output handling uses local Pydantic validation, consistent with the
[OpenAI structured-output guidance](https://developers.openai.com/api/docs/guides/structured-outputs).
The ChatGPT adapter currently requests JSON in the prompt; it does not claim
provider-enforced strict-schema generation.
