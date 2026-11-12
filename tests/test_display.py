from ui.display import analysis_label, element_label, evidence_text, workflow_visual


def test_readable_labels_and_workflow_evidence():
    analysis = {
        "source": "The exact user query, with its original details.",
        "sentences": [{"id": "S1", "text": "The reviewer approves the request."}],
        "process": {
            "states": [
                {
                    "id": "review",
                    "name": "Review request",
                    "kind": "start",
                    "actor": "Reviewer",
                    "evidence": ["S1"],
                    "inferred": False,
                }
            ],
            "transitions": [
                {
                    "id": "t1",
                    "source": "review",
                    "target": "review",
                    "condition": "Needs changes",
                    "label": "Revise",
                    "evidence": ["S1"],
                }
            ],
        },
    }
    row = {"id": "opaque-id", "created_at": "2026-11-12T12:00:00Z", "analysis": analysis}
    assert "The exact user query" in analysis_label(row)
    assert "opaque-id" not in analysis_label(row)
    assert (
        element_label(analysis["process"]["transitions"][0], {"review": "Review request"})
        == "Review request → Review request · Needs changes"
    )
    assert evidence_text({"evidence": ["S1", "S99"]}, analysis["sentences"]) == [
        "The reviewer approves the request.",
        "Source passage unavailable",
    ]
    visual = workflow_visual(analysis)
    assert visual["nodes"][0]["details"]["source_passages"] == [
        "The reviewer approves the request."
    ]
    assert visual["edges"][0]["details"]["source_passages"] == [
        "The reviewer approves the request."
    ]
