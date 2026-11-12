"""Manually specified structural cases, independent of production prompts.

These check verifier behavior, not hosted extraction accuracy. Evidence annotations
are intentionally coarse S1 references and must not be reported as semantic scores.
"""

import json
from pathlib import Path

import pytest

from app.engine import Rule, verify
from app.models import ProcessModel
from app.preprocessing import sentences

CASES = json.loads((Path(__file__).parent / "fixtures" / "evaluation.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_labeled_structural_cases(case):
    actor = case.get("actor", "clerk")
    shared = {"actor": actor, "evidence": ["S1"], "inferred": False, "inference_reason": None}
    process = ProcessModel.model_validate(
        {
            "process_id": case["name"],
            "actors": [actor] if actor else [],
            "states": [
                {"id": identifier, "name": identifier, "kind": kind, **shared}
                for identifier, kind in case["states"]
            ],
            "transitions": [
                {
                    "id": f"t{i}",
                    "source": source,
                    "target": target,
                    "condition": condition,
                    "label": "next",
                    **shared,
                }
                for i, (source, target, condition) in enumerate(case["edges"], 1)
            ],
        }
    )
    findings = verify(
        process,
        sentences(case["source"]),
        [Rule.model_validate(rule) for rule in case.get("rules", [])],
    )
    actual = {(finding.type, finding.location) for finding in findings}
    assert {tuple(item) for item in case["expected"]} <= actual
    if case["name"] in {"sequential", "approval_rejection", "multi_stage", "cycle"}:
        assert not {"dead_end", "unreachable_state", "missing_branch", "bypass"} & {
            finding.type for finding in findings
        }
