"""Readable presentation helpers for saved analyses and workflow details."""


def analysis_label(row: dict) -> str:
    """Describe a saved analysis using the actual source and creation time."""
    source = " ".join(row["analysis"]["source"].split())
    date = row.get("created_at", "")[:19].replace("T", " ")
    process = row["analysis"]["process"]
    counts = f"{len(process['states'])} steps, {len(process['transitions'])} transitions"
    return f"{source[:110]}{'…' if len(source) > 110 else ''}  ·  {counts}  ·  {date}"


def simulation_operations(process: dict) -> list[str]:
    """Offer only edits with an actual target in this saved snapshot."""
    operations = ["remove_transition", "change_transition"] if process["transitions"] else []
    if process["states"]:
        operations.append("remove_state")
    return operations


def element_label(element: dict, names: dict[str, str]) -> str:
    """Give a human-readable name to a workflow step or transition."""
    if "source" in element:
        return f"{names.get(element['source'], element['source'])} → {names.get(element['target'], element['target'])} · {element.get('condition') or element.get('label') or 'Next'}"
    return element.get("name", "Unnamed step")


def evidence_text(element: dict, ledger: list[dict]) -> list[str]:
    """Return source passages, preserving unknown-reference information."""
    mapping = {s["id"]: s["text"] for s in ledger}
    return [mapping.get(ref, "Source passage unavailable") for ref in element.get("evidence", [])]


def workflow_visual(analysis: dict) -> dict:
    """Build a canvas diagram directly from the saved workflow snapshot."""
    process = analysis["process"]
    return {
        "id": "saved-workflow",
        "kind": "workflow",
        "title": "Saved workflow",
        "note": "Based on the saved analysis. Source support and inferred steps require review.",
        "nodes": [
            {
                "id": s["id"],
                "label": s["name"],
                "details": {
                    **s,
                    "source_passages": evidence_text(s, analysis["sentences"]),
                },
            }
            for s in process["states"]
        ],
        "edges": [
            {
                "id": e["id"],
                "source": e["source"],
                "target": e["target"],
                "label": e.get("condition") or e.get("label") or "",
                "details": {
                    **e,
                    "source_passages": evidence_text(e, analysis["sentences"]),
                },
            }
            for e in process["transitions"]
        ],
    }
