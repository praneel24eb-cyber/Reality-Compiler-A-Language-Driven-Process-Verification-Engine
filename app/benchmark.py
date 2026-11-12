"""Small annotated comparison; gold annotations never enter provider prompts."""

import json
import re
from hashlib import sha256
from pathlib import Path
from time import perf_counter

from pydantic import Field

from app.evaluation import precision_recall
from app.llm import PROMPT, ExtractionError, LLMClient, ResponseType
from app.models import Contract, ProcessModel, Sentence
from app.pipeline import compile_sop
from app.preprocessing import sentences

CASES = json.loads(Path(__file__).with_name("benchmark_cases.json").read_text(encoding="utf-8"))
SCORED_DEFECTS = {"missing_branch", "unstated_actor", "dead_end", "unreachable_state", "bypass", "invariant_violation"}


class BaselinePrediction(Contract):
    process: ProcessModel
    defects: list[str] = Field(default_factory=list, max_length=40)


class BenchmarkRequest(Contract):
    case_ids: list[str] = Field(min_length=1, max_length=3)


class CountedClient:
    """Count logical model calls, including a corrective pass, not transport retries."""

    def __init__(self, client: LLMClient):
        self.client, self.calls = client, 0

    def extract(self, ledger: list[Sentence]) -> ProcessModel:
        self.calls += 1
        return self.client.extract(ledger)

    def structured(self, prompt: str, data: dict, schema: type[ResponseType]) -> ResponseType:
        self.calls += 1
        return self.client.structured(prompt, data, schema)


def summarize(rows: list[dict]) -> dict:
    """Macro averages across successful cases, with failure coverage kept explicit."""
    summary = {}
    for mode in ("plain_llm", "multipass_verified"):
        successful = [row[mode] for row in rows if row[mode]["status"] == "ok"]
        metrics = {}
        if successful:
            for metric in successful[0]["metrics"]:
                metrics[metric] = {
                    measure: sum(item["metrics"][metric][measure] for item in successful) / len(successful)
                    for measure in ("precision", "recall", "f1")
                }
        summary[mode] = {
            "successful_cases": len(successful), "failed_cases": len(rows) - len(successful),
            "macro_metrics_on_successes": metrics,
            "logical_model_calls": sum(row[mode]["logical_model_calls"] for row in rows),
            "latency_seconds": sum(row[mode]["latency_seconds"] for row in rows),
        }
    return summary


def normalize(value: str) -> str:
    return re.sub(r"\W+", " ", value.casefold()).strip()


def scores(process: ProcessModel, defects: set[str], case: dict) -> dict:
    names = {s.id: normalize(s.name) for s in process.states}
    metrics = {
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
    for metric in metrics.values():
        p, r = metric["precision"], metric["recall"]
        metric["f1"] = 2 * p * r / (p + r) if p + r else 0.0
    return metrics


def run_benchmark(client: LLMClient, requested: list[str]) -> dict:
    selected = [c for c in CASES if c["id"] in requested]
    if len(selected) != len(set(requested)):
        raise ValueError("Unknown benchmark case")
    results = []
    for case in selected:
        row = {"case": case["id"], "title": case["title"], "split": case.get("split", "seed"),
               "source_sha256": sha256(case["source"].encode()).hexdigest()}
        for mode in ("plain_llm", "multipass_verified"):
            counted = CountedClient(client)
            start = perf_counter()
            try:
                if mode == "plain_llm":
                    prediction = counted.structured(
                        PROMPT + " Also list detected defect types from: " + ", ".join(sorted(SCORED_DEFECTS)) + ". Do not invent missing routes.",
                        {"sentences": [s.model_dump() for s in sentences(case["source"])]},
                        BaselinePrediction,
                    )
                    process, defects = prediction.process, set(prediction.defects)
                else:
                    result = compile_sop(case["source"], counted, [])
                    process = result.process
                    defects = {f.type for f in result.findings if f.severity != "info"}
                row[mode] = {"status": "ok", "metrics": scores(process, defects, case),
                             "latency_seconds": perf_counter() - start,
                             "process": process.model_dump(), "defects": sorted(defects)}
                if mode == "multipass_verified":
                    row[mode]["stages"] = result.stages
            except (ExtractionError, ValueError) as exc:
                row[mode] = {"status": "failed", "error": str(exc), "latency_seconds": perf_counter() - start}
            row[mode]["logical_model_calls"] = counted.calls
        results.append(row)
    return {
        "cases": results,
        "summary": summarize(results),
        "dataset_sha256": sha256(json.dumps(CASES, sort_keys=True).encode()).hexdigest(),
        "methodology": "Same model, one logical call for plain-LLM extraction plus defect prediction versus two extraction/review calls plus deterministic verification; invalid references can add one correction call. Gold annotations excluded from prompts. Macro scores cover successful cases only; failures are reported separately. Logical calls exclude transport retries.",
        "limitations": "Nine author-annotated synthetic cases (three existing seeds and six frozen additional cases), not independent validation or a production accuracy estimate. One run per method does not measure sampling variance. Names use normalized exact match; synonyms can score as errors. Transition scores measure endpoints, not condition meaning. Evidence is scored for states. Defects are scored by category, not location. Empty/empty scores one. Manual source review remains necessary.",
    }
