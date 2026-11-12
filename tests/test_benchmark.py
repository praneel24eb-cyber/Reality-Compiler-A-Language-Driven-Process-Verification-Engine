from app.benchmark import CASES, run_benchmark, summarize
from app.llm import ExtractionError
from app.preprocessing import sentences


def test_annotations_reference_real_source_sentences():
    assert len(CASES) == len({case["id"] for case in CASES}) == 9
    for case in CASES:
        ids = {sentence.id for sentence in sentences(case["source"])}
        assert all(ref in ids and name in case["states"] for name, ref in case["state_evidence"])
        assert all(a in case["states"] and b in case["states"] for a, b in case["transitions"])


def test_failed_calls_are_counted_and_never_scored():
    class Unavailable:
        def structured(self, *args):
            raise ExtractionError("Provider unavailable")

        def extract(self, *args):
            raise ExtractionError("Provider unavailable")

    report = run_benchmark(Unavailable(), ["sequential"])
    for mode in ("plain_llm", "multipass_verified"):
        assert report["cases"][0][mode]["status"] == "failed"
        assert "metrics" not in report["cases"][0][mode]
        assert report["summary"][mode]["failed_cases"] == 1
        assert report["summary"][mode]["logical_model_calls"] == 1
        assert report["summary"][mode]["macro_metrics_on_successes"] == {}


def test_summary_reports_coverage_separately_from_accuracy():
    successful = {"status": "ok", "metrics": {"states": {"precision": .5, "recall": 1, "f1": 2/3}}, "logical_model_calls": 2, "latency_seconds": 3}
    failed = {"status": "failed", "logical_model_calls": 1, "latency_seconds": 4}
    report = summarize([{mode: result for mode in ("plain_llm", "multipass_verified")} for result in (successful, failed)])
    assert report["plain_llm"]["successful_cases"] == report["plain_llm"]["failed_cases"] == 1
    assert report["plain_llm"]["macro_metrics_on_successes"]["states"]["f1"] == 2/3
