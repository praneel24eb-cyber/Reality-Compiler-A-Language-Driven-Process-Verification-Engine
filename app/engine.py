"""Pure graph verification and copy-on-write scenarios."""

import hashlib
import re
from typing import Literal

import networkx as nx
from pydantic import Field

from app.models import Contract, Finding, ProcessModel, Sentence, State, Transition


class Rule(Contract):
    """Every start-to-target path must visit protected; target defaults to terminals."""

    protected: str
    target: str | None = None
    evidence: list[str] = Field(default_factory=list)


class Scenario(Contract):
    operation: Literal["remove_state", "remove_transition", "change_transition"]
    element_id: str
    label: str | None = None
    condition: str | None = None


class Analysis(Contract):
    source: str
    sentences: list[Sentence]
    process: ProcessModel
    findings: list[Finding]
    rules: list[Rule] = Field(default_factory=list)
    latency_seconds: float = 0
    pipeline_version: str = "legacy-single-pass"
    stages: list[str] = Field(default_factory=list)
    source_sha256: str | None = None
    extraction_draft: ProcessModel | None = None
    parent_analysis_id: str | None = None
    revision_reason: str | None = None
    origin: Literal["sop", "guided", "manual_revision"] = "sop"


def graph(process: ProcessModel) -> nx.MultiDiGraph:
    """Preserve distinct transition keys and all contract attributes."""
    result: nx.MultiDiGraph = nx.MultiDiGraph()
    for state in process.states:
        result.add_node(state.id, **state.model_dump())
    for edge in process.transitions:
        result.add_edge(edge.source, edge.target, key=edge.id, **edge.model_dump())
    return result


def reachable(process: ProcessModel) -> set[str]:
    """Reachability from all declared starts; bounded even with cycles."""
    g = graph(process)
    result: set[str] = set()
    for state in process.states:
        if state.kind == "start":
            result |= {state.id} | nx.descendants(g, state.id)
    return result


def verify(
    process: ProcessModel, ledger: list[Sentence], rules: list[Rule], *, allow_removed_rules: bool = False
) -> list[Finding]:
    """Report structural issues and conservative evidence review requirements."""
    results: list[Finding] = []

    def add(
        kind: str,
        location: str | None,
        message: str,
        evidence: list[str],
        path: list[str] | None = None,
        severity: str = "warning",
    ) -> None:
        key = hashlib.sha256(f"{kind}:{location}:{message}".encode()).hexdigest()[:16]
        results.append(
            Finding.model_validate(
                {
                    "id": key,
                    "type": kind,
                    "location": location,
                    "message": message,
                    "evidence": evidence,
                    "counterexample_path": path,
                    "severity": severity,
                }
            )
        )

    ids = {sentence.id for sentence in ledger}
    g = graph(process)
    starts = [state.id for state in process.states if state.kind == "start"]
    terminals = [state.id for state in process.states if state.kind == "terminal"]
    reached = reachable(process)

    def witness(target: str) -> list[str] | None:
        paths = [nx.shortest_path(g, s, target) for s in starts if nx.has_path(g, s, target)]
        return min(paths, key=len) if paths else None
    if len(starts) != 1:
        add(
            "invariant_violation",
            None,
            "Exactly one start state is required.",
            [],
            severity="error",
        )
    if not terminals:
        add("invariant_violation", None, "No terminal state is declared.", [])
    for sentence in ledger:
        if re.search(
            r"\b(parallel|simultaneously|concurrently|asynchronous|timer)\b",
            sentence.text,
            re.IGNORECASE,
        ):
            add(
                "unsupported_element",
                sentence.id,
                "Source may describe unsupported concurrency, events, or timers; review required.",
                [sentence.id],
            )
    elements: list[State | Transition] = [*process.states, *process.transitions]
    for element in elements:
        if not set(element.evidence) <= ids:
            add(
                "unsupported_element",
                element.id,
                "Evidence contains unknown sentence IDs.",
                element.evidence,
                severity="error",
            )
        else:
            add(
                "unsupported_element",
                element.id,
                "Evidence is linked, but semantic support requires human review.",
                element.evidence,
                severity="info",
            )
        if element.inferred:
            add("assumption", element.id, element.inference_reason or "", element.evidence)
        if not element.actor or element.actor not in process.actors:
            add("unstated_actor", element.id, "Actor is absent or not declared.", element.evidence)
    for state in process.states:
        outgoing = [edge for edge in process.transitions if edge.source == state.id]
        if state.id not in reached:
            add(
                "unreachable_state",
                state.id,
                "Unreachable from declared start states.",
                state.evidence,
            )
        if state.kind != "terminal" and not outgoing:
            add(
                "dead_end",
                state.id,
                "Nonterminal state has no outgoing transition.",
                state.evidence,
                witness(state.id),
            )
        if state.kind == "terminal" and outgoing:
            add(
                "invariant_violation",
                state.id,
                "Terminal state has outgoing transitions.",
                state.evidence,
                (witness(state.id) or [state.id]) + [outgoing[0].target],
            )
        if state.kind == "start" and g.in_degree(state.id):
            add(
                "invariant_violation",
                state.id,
                "Start state has incoming transitions.",
                state.evidence,
            )
        conditional = [edge for edge in outgoing if edge.condition]
        if conditional and len(outgoing) == 1:
            add(
                "missing_branch",
                state.id,
                "Conditional exit has no alternative branch.",
                state.evidence,
                witness(state.id),
            )
        elif conditional:
            add(
                "assumption",
                state.id,
                "Condition exhaustiveness and exclusivity require human review.",
                state.evidence,
            )
        normalized = [e.condition.strip().casefold() for e in conditional if e.condition]
        if len(normalized) != len(set(normalized)):
            add("invariant_violation", state.id, "Multiple exits use the same condition.",
                state.evidence, witness(state.id))
    can_finish = set(terminals)
    for terminal in terminals:
        can_finish |= nx.ancestors(g, terminal)
    for component in nx.strongly_connected_components(g):
        cyclic = len(component) > 1 or any(g.has_edge(s, s) for s in component)
        if cyclic and component & reached and not component & can_finish:
            target = min(component)
            add("dead_end", target, "Reachable cycle has no path to a terminal state.",
                next(s.evidence for s in process.states if s.id == target), witness(target), "error")
    for rule in rules:
        if rule.protected not in g or (rule.target is not None and rule.target not in g):
            if not allow_removed_rules:
                raise ValueError("Verification rule references an unknown state")
            add("invariant_violation", rule.protected,
                "A state referenced by a required-step rule was removed.", [], severity="error")
            if rule.target is not None and rule.target not in g:
                continue
        reduced = g.copy()
        if rule.protected in reduced:
            reduced.remove_node(rule.protected)
        for start in starts:
            for target in [rule.target] if rule.target else terminals:
                if start in reduced and target in reduced and nx.has_path(reduced, start, target):
                    add(
                        "bypass",
                        rule.protected,
                        f"Path to {target} bypasses required state {rule.protected}.",
                        [],
                        nx.shortest_path(reduced, start, target),
                        "error",
                    )
    return sorted(results, key=lambda finding: finding.id)


def simulate(original: Analysis, scenario: Scenario) -> dict:
    """Apply a supported edit to a deep copy and compare deterministic findings."""
    data = original.process.model_dump()
    collection = "states" if scenario.operation == "remove_state" else "transitions"
    if not any(item["id"] == scenario.element_id for item in data[collection]):
        raise ValueError("Scenario element does not exist")
    if scenario.operation == "remove_state":
        data["states"] = [item for item in data["states"] if item["id"] != scenario.element_id]
        data["transitions"] = [
            edge
            for edge in data["transitions"]
            if scenario.element_id not in (edge["source"], edge["target"])
        ]
    elif scenario.operation == "remove_transition":
        data["transitions"] = [
            edge for edge in data["transitions"] if edge["id"] != scenario.element_id
        ]
    else:
        fields = scenario.model_fields_set & {"label", "condition"}
        if not fields or ("label" in fields and scenario.label is None):
            raise ValueError("Supply a label or condition; label cannot be null")
        for edge in data["transitions"]:
            if edge["id"] == scenario.element_id:
                edge.update({field: getattr(scenario, field) for field in fields})
    process = ProcessModel.model_validate(data)
    findings = verify(process, original.sentences, original.rules, allow_removed_rules=True)
    # Semantic review cannot be rerun deterministically. Retain relevant review warnings.
    locations = {s.id for s in process.states} | {e.id for e in process.transitions}
    findings += [f for f in original.findings if f.method == "llm_review"
                 and (f.location is None or f.location in locations)]
    old = {finding.id for finding in original.findings}
    new = {finding.id for finding in findings}
    return {
        "process": process.model_dump(),
        "findings": [f.model_dump() for f in findings],
        "new_findings": [f.model_dump() for f in findings if f.id not in old],
        "resolved_findings": [f.model_dump() for f in original.findings if f.id not in new],
        "lost_reachability": sorted(reachable(original.process) - reachable(process)),
        "gained_reachability": sorted(reachable(process) - reachable(original.process)),
    }
