"""Evidence-focused workspace for building, inspecting and verifying processes."""

import json
import os
from pathlib import Path

import graphviz
import httpx
import streamlit as st

from app.documents import pdf_pages
from app.preprocessing import sentences
from ui.api_errors import request_error
from ui.builder import builder_page
from ui.canvas import board_component, canvas_page
from ui.connection import connection_page
from ui.display import (
    analysis_label,
    element_label,
    evidence_text,
    simulation_operations,
    workflow_visual,
)
from ui.editor import workflow_editor
from ui.evaluation import evaluation_page
from ui.theme import apply_theme

BASE = os.getenv("API_URL", "http://127.0.0.1:8000")


def api(path, payload=None):
    try:
        with httpx.Client(timeout=300) as client:
            response = (
                client.get(BASE + path)
                if payload is None
                else client.post(BASE + path, json=payload)
            )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        st.error(request_error(exc))
        st.stop()


def selected():
    rows = api("/analyses")
    if not rows:
        st.info("Analyze an SOP first.")
        st.stop()
    ids = [row["id"] for row in rows]
    labels = {row["id"]: analysis_label(row) for row in rows}
    identifier = st.selectbox("Saved workflow", ids, format_func=lambda item: labels[item])
    row = next(row for row in rows if row["id"] == identifier)
    with st.expander("View exact original SOP / query"):
        st.text(row["analysis"]["source"])
    return row


def draw(process):
    dot = graphviz.Digraph()
    for state in process["states"]:
        dot.node(
            state["id"],
            state["name"],
            shape={"start": "ellipse", "normal": "box", "terminal": "doublecircle"}[state["kind"]],
        )
    for edge in process["transitions"]:
        dot.edge(
            edge["source"],
            edge["target"],
            label=edge["condition"] or edge["label"],
        )
    st.graphviz_chart(dot)


def dashboard():
    st.title("Executive Dashboard")
    rows = api("/analyses")
    findings = [finding for row in rows for finding in row["analysis"]["findings"]]
    st.metric("Saved workflows", len(rows))
    st.metric("Findings", len(findings))
    columns = st.columns(3)
    for column, severity in zip(columns, ["error", "warning", "info"]):
        column.metric(severity.capitalize(), sum(f["severity"] == severity for f in findings))
    total = linked = 0
    for row in rows:
        analysis = row["analysis"]
        ids = {s["id"] for s in analysis["sentences"]}
        for element in analysis["process"]["states"] + analysis["process"]["transitions"]:
            total += 1
            linked += bool(element["evidence"]) and set(element["evidence"]) <= ids
    st.metric("Valid evidence links (not semantic proof)", f"{linked}/{total}")
    st.subheader("Recent workflows")
    for row in rows[:10]:
        st.write(analysis_label(row))
    st.page_link(input_page, label="Analyze SOP")


def studio():
    st.title("SOP Input Studio")
    upload = st.file_uploader("Upload an SOP PDF or UTF-8 text file", type=["pdf", "txt"])
    if upload is not None:
        if upload.size > 10_000_000:
            st.error("File exceeds 10 MB.")
        elif upload.name.lower().endswith(".pdf"):
            try:
                pages = pdf_pages(upload.getvalue())
                selected_pages = st.multiselect(
                    "Pages to analyze (1-based)", list(range(1, len(pages) + 1))
                )
                if st.button("Load selected pages", disabled=not selected_pages):
                    text = "\n\n".join(pages[i - 1] for i in sorted(selected_pages))
                    if len(text) > 30000:
                        st.error("Select fewer pages: analysis limit is 30,000 characters.")
                    else:
                        st.session_state["source"] = text
                st.caption(
                    "Text extraction only. Review the editor for reading order and missing diagrams before analysis."
                )
            except ValueError as exc:
                st.error(str(exc))
        elif st.button("Load uploaded text"):
            try:
                text = upload.getvalue().decode("utf-8-sig")
                if len(text) > 30000:
                    st.error("Select a shorter SOP: 30,000 character limit.")
                else:
                    st.session_state["source"] = text
            except UnicodeDecodeError:
                st.error("Use a UTF-8 text file.")
    hbl = Path("testing/hbl/purchase-manual-sop.pdf")
    if hbl.exists() and st.button("Load HBL material receipt section (public SOP)"):
        pages = pdf_pages(hbl.read_bytes())
        section = pages[9].split("Material receipt", 1)[-1]
        section = "Material receipt" + section + "\n" + pages[10].split("Sub Contract", 1)[0]
        st.session_state["source"] = section
        st.info(
            "Loaded material receipt and acceptance/rejection text from PDF pages 10–11. Review before analysis. Source: https://hbl.in/purchase-manual-sop.pdf"
        )
    if st.button("Use synthetic sample"):
        st.session_state["source"] = (
            "The clerk receives a request. The manager reviews it. The clerk archives it."
        )
    source = st.text_area("Original SOP", key="source", height=250, max_chars=30000)
    st.caption(f"{len(source)} characters")
    if source.strip():
        try:
            with st.expander("Preview source passages"):
                for sentence in sentences(source):
                    st.write(sentence.text)
        except ValueError as exc:
            st.error(str(exc))
            return
    st.caption("Explicit mandatory steps are extracted from the source. Review or add required-step rules by name in Workflow Explorer after analysis.")
    if st.button("Analyze and save", disabled=not source.strip()):
        with st.spinner("Extracting and verifying workflow"):
            saved = api("/analyses", {"source": source, "rules": []})
        process = saved["analysis"]["process"]
        if not process["transitions"]:
            st.warning(
                "Saved for review, but no transitions were extracted. Cover pages and contents "
                "pages may not describe a procedure. Load the pages with actual steps and "
                "analyze them before running transition simulations."
            )
        else:
            st.success(
                f"Saved {len(process['states'])} steps and {len(process['transitions'])} "
                "transitions. Open Workflow Explorer or AI Canvas to explore it."
            )


def inspector():
    st.title("Extraction Inspector")
    analysis = selected()["analysis"]
    with st.expander("Source passages"):
        for sentence in analysis["sentences"]:
            st.write(sentence["text"])
            if sentence.get("start") is not None:
                st.caption(f"Original text characters {sentence['start']}–{sentence['end']} (end excluded)")
    st.subheader("People and teams")
    st.write(", ".join(analysis["process"]["actors"]) or "Not stated")
    names = {state["id"]: state["name"] for state in analysis["process"]["states"]}
    st.subheader("Workflow steps")
    st.dataframe(
        [
            {
                "Step": s["name"],
                "Type": s["kind"].capitalize(),
                "Actor": s.get("actor") or "Not stated",
                "Inferred": "Yes" if s["inferred"] else "No",
            }
            for s in analysis["process"]["states"]
        ],
        hide_index=True,
    )
    st.subheader("Transitions")
    st.dataframe(
        [
            {
                "From": names.get(e["source"], e["source"]),
                "To": names.get(e["target"], e["target"]),
                "Condition": e.get("condition") or e.get("label") or "—",
                "Actor": e.get("actor") or "Not stated",
            }
            for e in analysis["process"]["transitions"]
        ],
        hide_index=True,
    )
    elements = analysis["process"]["states"] + analysis["process"]["transitions"]
    if elements:
        index = st.selectbox(
            "Inspect a step or transition",
            range(len(elements)),
            format_func=lambda i: element_label(elements[i], names),
        )
        element = elements[index]
        st.write("**Actor:**", element.get("actor") or "Not stated")
        if element.get("condition"):
            st.write("**Condition:**", element["condition"])
        st.write("**Inferred:**", "Yes" if element["inferred"] else "No")
        if element.get("inference_reason"):
            st.write("**Reason:**", element["inference_reason"])
        st.subheader("Linked source passages")
        for passage in evidence_text(element, analysis["sentences"]):
            st.write(passage)
        findings = [f for f in analysis["findings"] if f["location"] == element["id"]]
        if findings:
            st.subheader("Related findings")
            for finding in findings:
                st.write(f"{finding['severity'].capitalize()}: {finding['message']}")


def explorer():
    st.title("Workflow Explorer")
    row = selected()
    analysis = row["analysis"]
    workflow_editor(row, api)
    layouts = st.session_state.setdefault("explorer_layouts", {})
    component_key = "explorer_board_" + row["id"]

    def save_explorer_layout():
        layouts[row["id"]] = st.session_state[component_key].get("layout", {})

    st.caption(
        "Drag the diagram card, use zoom controls, and select a step or transition for details."
    )
    board_component(
        data={
            "messages": [],
            "visuals": [workflow_visual(analysis)],
            "layout": layouts.get(row["id"], {}),
            "error": "",
            "diagram_only": True,
        },
        key=component_key,
        on_layout_change=save_explorer_layout,
        on_submit_change=lambda: None,
        on_remove_change=lambda: None,
    )
    with st.expander("Associated findings"):
        for finding in analysis["findings"]:
            st.write(f"{finding['severity'].capitalize()}: {finding['message']}")
    with st.expander("Version history and provenance"):
        for version in api(f"/analyses/{row['id']}/versions"):
            a = version["analysis"]
            st.write(version["created_at"], a.get("revision_reason") or "Original analysis")
            st.caption(" → ".join(a.get("stages", [])) or "Legacy single-pass analysis")


def verification():
    st.title("Verification Center")
    analysis = selected()["analysis"]
    names = {s["id"]: s["name"] for s in analysis["process"]["states"]}
    if analysis["rules"]:
        st.subheader("Required-step rules used by the verifier")
        for rule in analysis["rules"]:
            st.write(f"{names.get(rule['protected'], rule['protected'])} must occur before {names.get(rule.get('target'), 'every terminal outcome')}.")
            for passage in evidence_text(rule, analysis["sentences"]):
                st.write(passage)
    for severity in ["error", "warning", "info"]:
        st.subheader(severity.capitalize())
        for finding in [f for f in analysis["findings"] if f["severity"] == severity]:
            st.write(f"**{finding['type'].replace('_', ' ').capitalize()}** — {finding['message']}")
            st.caption("AI source review — confirm against the procedure" if finding.get("method") == "llm_review" else "Deterministic structural check")
            for passage in evidence_text(finding, analysis["sentences"]):
                st.write(passage)
            if finding.get("counterexample_path"):
                names = {s["id"]: s["name"] for s in analysis["process"]["states"]}
                st.write(
                    "Path: "
                    + " → ".join(names.get(item, item) for item in finding["counterexample_path"])
                )


def lab():
    st.title("What-If Simulation Lab")
    row = selected()
    st.caption("Scenarios are saved separately; the original is never overwritten.")
    process = row["analysis"]["process"]
    st.write(f"{len(process['states'])} steps · {len(process['transitions'])} transitions")
    if not process["transitions"]:
        st.warning(
            "This saved analysis has no transitions to remove or change. It may contain only "
            "cover/index pages or incomplete procedure text. Select a saved workflow with "
            "transitions, or load the procedure pages in SOP Input Studio and analyze them."
        )
        st.page_link(input_page, label="Open SOP Input Studio")
    operations = simulation_operations(process)
    if not operations:
        st.info("There are no workflow steps to simulate. Analyze the procedure pages first.")
        return
    operation = st.selectbox(
        "Operation", operations,
        format_func=lambda value: value.replace("_", " ").capitalize(),
        key="scenario_operation_" + row["id"],
    )
    collection = "states" if operation == "remove_state" else "transitions"
    ids = [item["id"] for item in row["analysis"]["process"][collection]]
    items = row["analysis"]["process"][collection]
    names = {s["id"]: s["name"] for s in row["analysis"]["process"]["states"]}
    identifier = st.selectbox(
        "Element",
        ids,
        format_func=lambda value: element_label(
            next(item for item in items if item["id"] == value), names
        ),
    )
    payload = {"operation": operation, "element_id": identifier}
    if operation == "change_transition":
        field = st.selectbox("Field to change", ["label", "condition"])
        payload[field] = st.text_input("New value")
        if field == "condition" and st.checkbox("Remove condition"):
            payload[field] = None
    if st.button("Run scenario"):
        result = api(f"/analyses/{row['id']}/scenarios", payload)
        left, right = st.columns(2)
        with left:
            st.write("Saved original")
            draw(row["analysis"]["process"])
        with right:
            st.write("Scenario")
            draw(result["process"])
        for key in [
            "new_findings",
            "resolved_findings",
            "lost_reachability",
            "gained_reachability",
        ]:
            st.subheader(key.replace("_", " ").capitalize())
            for item in result[key]:
                st.write(
                    item.get("message", "") if isinstance(item, dict) else names.get(item, item)
                )
            if not result[key]:
                st.caption("None")


def reports():
    st.title("Audit Report Center")
    row = selected()
    report = api(f"/analyses/{row['id']}/report")
    st.warning(report["limitations"])
    analysis = report["analysis"]
    st.subheader("Original SOP / query")
    st.text(analysis["source"])
    st.subheader("Workflow")
    draw(analysis["process"])
    st.subheader("Findings")
    for finding in analysis["findings"]:
        st.write(f"{finding['severity'].capitalize()} — {finding['message']}")
    st.subheader("Methodology")
    st.write(report["methodology"])
    st.download_button(
        "Download audit report",
        json.dumps(report, indent=2),
        file_name="audit-report.json",
        mime="application/json",
    )


st.set_page_config(page_title="Reality Compiler", page_icon="◈", layout="wide")
apply_theme()
input_page = st.Page(studio, title="SOP Input Studio", icon=":material/upload_file:")
st.navigation(
    [
        st.Page(canvas_page, title="AI Canvas", icon=":material/dashboard_customize:"),
        st.Page(builder_page, title="Workflow Builder", icon=":material/add_circle:"),
        st.Page(connection_page, title="ChatGPT Connection", icon=":material/link:"),
        st.Page(dashboard, title="Executive Dashboard", icon=":material/space_dashboard:"),
        input_page,
        st.Page(inspector, title="Extraction Inspector", icon=":material/find_in_page:"),
        st.Page(explorer, title="Workflow Explorer", icon=":material/account_tree:"),
        st.Page(verification, title="Verification Center", icon=":material/verified_user:"),
        st.Page(lab, title="What-If Simulation Lab", icon=":material/science:"),
        st.Page(reports, title="Audit Report Center", icon=":material/description:"),
        st.Page(evaluation_page, title="Evaluation & Benchmarking", icon=":material/query_stats:"),
    ]
).run()
