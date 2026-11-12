"""Readable editing controls; every save creates a separate analysis version."""

from copy import deepcopy
from uuid import uuid4

import streamlit as st

from ui.display import element_label


def workflow_editor(row, api):
    analysis = row["analysis"]
    with st.expander("Edit workflow or required-step rules"):
        st.caption("Saving creates a new version. Edited elements are marked as user revisions; source links are retained for review.")
        process = deepcopy(analysis["process"])
        names = {s["id"]: s["name"] for s in process["states"]}
        operation = st.selectbox("Edit", ["Step", "Transition", "Add step", "Add transition", "Required-step rules"])
        if operation in {"Step", "Transition"}:
            items = process["states"] if operation == "Step" else process["transitions"]
            if not items:
                st.info("No elements of this type are available. Add one first.")
                return
            index = st.selectbox("Choose element", range(len(items)), format_func=lambda i: element_label(items[i], names))
            element = items[index]
        else:
            element = {}
        with st.form("workflow_edit_" + row["id"] + operation):
            if operation == "Required-step rules":
                if not names:
                    st.info("Add workflow steps before defining a rule.")
                    return
                for rule in analysis["rules"]:
                    st.write(f"Required: {names.get(rule['protected'], rule['protected'])} before {names.get(rule.get('target'), 'every terminal outcome')}")
                protected = st.selectbox("Step that must not be skipped", list(names), format_func=lambda v: names[v])
                target = st.selectbox("Before reaching", [None] + list(names), format_func=lambda v: names.get(v, "Every terminal outcome"))
                replace = st.checkbox("Replace existing rules with this rule")
            else:
                is_state = operation in {"Step", "Add step"}
                if is_state:
                    name = st.text_input("Step name", value=element.get("name", ""))
                    kinds = ["start", "normal", "terminal"]
                    kind = st.selectbox("Step type", kinds, index=kinds.index(element.get("kind", "normal")))
                else:
                    if not names:
                        st.info("Add steps before connecting them.")
                        return
                    ids = list(names)
                    source = st.selectbox("From step", ids, format_func=lambda v: names[v], index=ids.index(element.get("source", ids[0])))
                    target = st.selectbox("To step", ids, format_func=lambda v: names[v], index=ids.index(element.get("target", ids[-1])))
                    label = st.text_input("Action", value=element.get("label", ""))
                    condition = st.text_input("Condition (blank for unconditional)", value=element.get("condition") or "")
                actor = st.text_input("Responsible person or team (blank if unknown)", value=element.get("actor") or "")
                passages = {s["id"]: s["text"] for s in analysis["sentences"]}
                evidence = st.multiselect("Source passages supporting this element", list(passages), default=element.get("evidence", []), format_func=lambda v: passages[v])
            reason = st.text_input("Reason for this version")
            save = st.form_submit_button("Save as a new version")
        if save:
            if not reason.strip():
                st.error("Enter a reason for the change.")
                return
            payload: dict = {"reason": reason}
            if operation == "Required-step rules":
                rule = {"protected": protected, "target": target}
                payload["rules"] = [rule] if replace else analysis["rules"] + ([rule] if rule not in analysis["rules"] else [])
            else:
                if not evidence or (is_state and not name.strip()):
                    st.error("Enter a step name and choose supporting source passages.")
                    return
                element.update({"actor": actor.strip() or None, "evidence": evidence})
                if actor.strip() and actor.strip() not in process["actors"]:
                    process["actors"].append(actor.strip())
                if is_state:
                    element.update({"name": name, "kind": kind})
                else:
                    element.update({"source": source, "target": target, "label": label, "condition": condition.strip() or None})
                if operation.startswith("Add"):
                    element.update({"id": "user_" + uuid4().hex[:12], "inferred": True, "inference_reason": "User revision: " + reason})
                    process["states" if is_state else "transitions"].append(element)
                payload["process"] = process
            saved = api(f"/analyses/{row['id']}/versions", payload)
            st.success("New version saved. Select the newest saved workflow to explore it.")
            st.caption(f"{len(saved['analysis']['process']['states'])} steps · {len(saved['analysis']['process']['transitions'])} transitions")
