"""Small annotated comparison; gold annotations never enter provider prompts."""

import json
import re
from pathlib import Path
from time import perf_counter

from pydantic import Field

from app.evaluation import precision_recall
from app.llm import PROMPT, ExtractionError, LLMClient
from app.models import Contract, ProcessModel
from app.pipeline import compile_sop
from app.preprocessing import sentences

CASES = json.loads(Path(__file__).with_name("benchmark_cases.json").read_text(encoding="utf-8"))
SCORED_DEFECTS = {"missing_branch", "unstated_actor", "dead_end", "unreachable_state", "bypass", "invariant_violation"}


class BaselinePrediction(Contract):
    process: ProcessModel
    defects: list[str] = Field(default_factory=list, max_length=40)


class BenchmarkRequest(Contract):
    case_ids: list[str] = Field(min_length=1, max_length=3)


def normalize(value: str) -> str:
    return re.sub(r"\W+", " ", value.casefold()).strip()


def scores(process: ProcessModel, defects: set[str], case: dict) -> dict:
    names = {s.id: normalize(s.name) for s in process.states}
    return {
        "states": precision_recall(names.values(), map(normalize, case["states"])),
        "transitions": precision_recall(
            [(names[e.source], names[e.target]) for e in process.transitions],
            [(normalize(a), normalize(b)) for a, b in case["transitions"]],
        ),
        "actors": precision_recall(map(normalize, process.actors), map(normalize, case["actors"])),
        "state_evidence": precision_recall(
            [(names[s.id], ref) for s in process.states for ref in s.evidence],
            [(normalize(name), ref) for name, ref in case["state_evidence"]],
        ),
        "defect_types": precision_recall(defects & SCORED_DEFECTS, case["defects"]),
    }


def run_benchmark(client: LLMClient, requested: list[str]) -> dict:
    selected = [c for c in CASES if c["id"] in requested]
    if len(selected) != len(set(requested)):
        raise ValueError("Unknown benchmark case")
    results = []
    for case in selected:
        row = {"case": case["id"], "title": case["title"]}
        for mode in ("plain_llm", "multipass_verified"):
            start = perf_counter()
            try:
                if mode == "plain_llm":
                    prediction = client.structured(
                        PROMPT + " Also list detected defect types from: " + ", ".join(sorted(SCORED_DEFECTS)) + ". Do not invent missing routes.",
                        {"sentences": [s.model_dump() for s in sentences(case["source"])]},
                        BaselinePrediction,
                    )
                    process, defects = prediction.process, set(prediction.defects)
                else:
                    result = compile_sop(case["source"], client, [])
                    process = result.process
                    defects = {f.type for f in result.findings if f.severity != "info"}
                row[mode] = {"status": "ok", "metrics": scores(process, defects, case),
                             "latency_seconds": perf_counter() - start,
                             "process": process.model_dump(), "defects": sorted(defects)}
            except (ExtractionError, ValueError) as exc:
                row[mode] = {"status": "failed", "error": str(exc), "latency_seconds": perf_counter() - start}
        results.append(row)
    return {
        "cases": results,
        "methodology": "Same model, one call for plain-LLM extraction plus defect prediction versus two extraction/review calls plus deterministic verification. Gold annotations excluded from prompts.",
        "limitations": "Three synthetic seed cases, not a production accuracy estimate. Names use normalized exact match; synonyms can score as errors. Transition scores measure endpoints, not condition meaning. Evidence is scored for states. Defects are scored by category, not location. Manual source review remains necessary.",
    }
