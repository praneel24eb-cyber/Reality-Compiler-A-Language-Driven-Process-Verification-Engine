"""Immutable user-reviewed process revisions."""

from pydantic import Field

from app.engine import Analysis, Rule, verify
from app.models import Contract, ProcessModel, State, Transition
from app.pipeline import validate_evidence


class RevisionRequest(Contract):
    process: ProcessModel | None = None
    rules: list[Rule] | None = None
    reason: str = Field(min_length=1, max_length=1000, pattern=r"\S")


def revise(original: Analysis, parent_id: str, request: RevisionRequest) -> Analysis:
    if request.process is None and request.rules is None:
        raise ValueError("Supply workflow edits or required-step rules")
    process = (request.process or original.process).model_copy(deep=True)
    previous: dict[tuple[str, str], State | Transition] = {("state", s.id): s for s in original.process.states}
    previous.update({("transition", e.id): e for e in original.process.transitions})
    elements: list[tuple[str, State | Transition]] = [("state", s) for s in process.states] + [("transition", e) for e in process.transitions]
    for kind, element in elements:
        if previous.get((kind, element.id)) != element:
            element.inferred = True
            element.inference_reason = "User revision: " + request.reason
    validate_evidence(process, original.sentences)
    rules = request.rules if request.rules is not None else original.rules
    findings = verify(process, original.sentences, rules, allow_removed_rules=request.rules is None)
    locations = {s.id for s in process.states} | {e.id for e in process.transitions}
    findings += [f.model_copy(update={"message": "Prior AI review; re-check after edits: " + f.message})
                 for f in original.findings if f.method == "llm_review"
                 and (f.location is None or f.location in locations)]
    result = original.model_copy(deep=True)
    result.process, result.rules, result.findings = process, rules, findings
    result.parent_analysis_id = parent_id
    result.revision_reason = request.reason
    result.origin = "manual_revision"
    result.stages = ["user_revision", "evidence_validation", "graph_verification"]
    result.extraction_draft = None
    result.latency_seconds = 0
    return result
