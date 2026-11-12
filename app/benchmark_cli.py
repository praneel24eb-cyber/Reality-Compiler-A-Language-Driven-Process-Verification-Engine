"""Run the live comparison through the local API, checkpointing after every case."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.benchmark import CASES, summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", action="append", choices=[c["id"] for c in CASES])
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new output filename to preserve previous results")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report: dict = {"cases": [], "started_at": datetime.now(UTC).isoformat()}
    with httpx.Client(base_url=args.api, timeout=600) as client:
        for case in args.case or [c["id"] for c in CASES]:
            response = client.post("/evaluation/run", json={"case_ids": [case]})
            response.raise_for_status()
            payload = response.json()
            report.update({k: v for k, v in payload.items() if k not in {"cases", "summary"}})
            report["cases"].extend(payload["cases"])
            report["summary"] = summarize(report["cases"])
            report["updated_at"] = datetime.now(UTC).isoformat()
            status = client.get("/auth/chatgpt/status")
            status.raise_for_status()
            report["model"] = status.json().get("model")
            temporary = args.output.with_suffix(".tmp")
            temporary.write_text(json.dumps(report, indent=2), encoding="utf-8")
            temporary.replace(args.output)
            row = payload["cases"][0]
            print(f"{case}: baseline={row['plain_llm']['status']}, reviewed={row['multipass_verified']['status']}", flush=True)


if __name__ == "__main__":
    main()
