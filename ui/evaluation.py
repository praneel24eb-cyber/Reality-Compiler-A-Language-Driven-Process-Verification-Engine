"""Visible comparison of annotated cases, without raw model payloads."""

import json
import os

import httpx
import streamlit as st

from app.benchmark import summarize
from ui.api_errors import request_error


def evaluation_page():
    st.title("Evaluation & Benchmarking")
    st.write("Compare a plain AI response with the reviewed and verified pipeline on annotated synthetic procedures.")
    base = os.getenv("API_URL", "http://127.0.0.1:8000")
    try:
        response = httpx.get(base + "/evaluation/cases", timeout=15)
        response.raise_for_status()
        cases = {c["id"]: c["title"] for c in response.json()}
        selected = st.multiselect("Test cases", list(cases), default=list(cases)[:3], format_func=lambda v: cases[v])
        st.caption(f"This comparison normally uses {len(selected) * 3} AI calls and your connected plan allowance. An invalid review may require one extra correction call per case.")
        if st.button("Run comparison", disabled=not selected):
            reports = []
            for identifier in selected:
                with st.spinner("Evaluating " + cases[identifier]):
                    response = httpx.post(base + "/evaluation/run", json={"case_ids": [identifier]}, timeout=300)
                    response.raise_for_status()
                    reports.append(response.json())
            st.session_state["benchmark_report"] = {**reports[0], "cases": [c for r in reports for c in r["cases"]]}
            st.session_state["benchmark_report"]["summary"] = summarize(st.session_state["benchmark_report"]["cases"])
        report = st.session_state.get("benchmark_report")
        if report:
            st.write(report["methodology"])
            st.warning(report["limitations"])
            rows = []
            for case in report["cases"]:
                for mode in ("plain_llm", "multipass_verified"):
                    result = case[mode]
                    if result["status"] != "ok":
                        st.error(f"{case['title']} / {mode.replace('_', ' ')}: {result['error']}")
                        continue
                    for metric, score in result["metrics"].items():
                        rows.append({"Case": case["title"], "Method": mode.replace("_", " "), "Metric": metric.replace("_", " "), **score})
            st.dataframe(rows, hide_index=True)
            st.download_button("Download benchmark report", json.dumps(report, indent=2), file_name="benchmark-report.json")
    except (httpx.HTTPError, ValueError) as exc:
        st.error(request_error(exc))
