from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

WORKFLOWS = {
    "Project Progress Update": {
        "states": ["Draft", "Submitted", "Under Review", "Approved", "Rejected"],
        "final": "Approved",
    },
    "Project Change Request": {
        "states": ["Draft", "Submitted", "Under Review", "Approved", "Rejected", "Implemented"],
        "final": "Implemented",
    },
    "Project Compliance Deliverable": {
        "states": ["Draft", "Submitted", "Under Review", "Approved", "Rejected", "Completed"],
        "final": "Completed",
    },
    "Project Beneficiary Plan": {
        "states": ["Draft", "Submitted", "Under Review", "Approved", "Rejected", "Finalized"],
        "final": "Finalized",
    },
    "Project Closure": {
        "states": ["Draft", "Submitted", "Under Review", "Approved", "Rejected", "Closed"],
        "final": "Closed",
    },
}

STATE_STYLES = {
    "Draft": "Primary", "Submitted": "Warning", "Under Review": "Warning",
    "Approved": "Success", "Rejected": "Danger", "Implemented": "Success",
    "Completed": "Success", "Finalized": "Success", "Closed": "Success",
}
ACTIONS = ["Submit for Review", "Start Review", "Approve", "Reject", "Return to Draft", "Mark Implemented", "Mark Completed", "Finalize", "Close"]


def _ensure_state(name):
    if not frappe.db.exists("Workflow State", {"workflow_state_name": name}):
        frappe.get_doc({"doctype":"Workflow State","workflow_state_name":name,"style":STATE_STYLES.get(name,"Primary")}).insert(ignore_permissions=True)


def _ensure_action(name):
    if not frappe.db.exists("Workflow Action Master", {"workflow_action_name": name}):
        frappe.get_doc({"doctype":"Workflow Action Master","workflow_action_name":name}).insert(ignore_permissions=True)


def _role_map():
    result={}
    if frappe.db.exists("DocType","Projects Settings"):
        settings=frappe.get_single("Projects Settings")
        if settings.meta.has_field("project_workflow_role_mappings"):
            for row in settings.get("project_workflow_role_mappings") or []:
                if row.enabled and row.process_doctype:
                    result[row.process_doctype]={
                        "owner":row.draft_owner_role or "System Manager",
                        "reviewer":row.reviewer_role or "System Manager",
                        "approver":row.approver_role or "System Manager",
                    }
    return result


def _transitions(states, roles):
    rows=[
        {"state":"Draft","action":"Submit for Review","next_state":"Submitted","allowed":roles["owner"]},
        {"state":"Submitted","action":"Start Review","next_state":"Under Review","allowed":roles["reviewer"]},
        {"state":"Under Review","action":"Approve","next_state":"Approved","allowed":roles["approver"]},
        {"state":"Under Review","action":"Reject","next_state":"Rejected","allowed":roles["approver"]},
        {"state":"Submitted","action":"Return to Draft","next_state":"Draft","allowed":roles["reviewer"]},
        {"state":"Rejected","action":"Return to Draft","next_state":"Draft","allowed":roles["owner"]},
    ]
    if "Implemented" in states: rows.append({"state":"Approved","action":"Mark Implemented","next_state":"Implemented","allowed":roles["owner"]})
    if "Completed" in states: rows.append({"state":"Approved","action":"Mark Completed","next_state":"Completed","allowed":roles["owner"]})
    if "Finalized" in states: rows.append({"state":"Approved","action":"Finalize","next_state":"Finalized","allowed":roles["owner"]})
    if "Closed" in states: rows.append({"state":"Approved","action":"Close","next_state":"Closed","allowed":roles["owner"]})
    return rows


def provision_project_workflows():
    # The field is created before Workflow insertion, including DocTypes whose original JSON omitted it.
    custom={}
    for dt in WORKFLOWS:
        if not frappe.db.exists("DocType",dt):
            continue
        if not frappe.get_meta(dt).has_field("workflow_state"):
            custom.setdefault(dt,[]).append({
                "fieldname":"workflow_state","label":"Workflow State","fieldtype":"Link",
                "options":"Workflow State","read_only":1,"allow_on_submit":1,
                "insert_after":"amended_from" if frappe.get_meta(dt).has_field("amended_from") else None,
            })
    if custom: create_custom_fields(custom,update=True)

    for state in sorted({x for spec in WORKFLOWS.values() for x in spec["states"]}): _ensure_state(state)
    for action in ACTIONS: _ensure_action(action)
    mappings=_role_map()
    for dt,spec in WORKFLOWS.items():
        if not frappe.db.exists("DocType",dt): continue
        name=dt
        if frappe.db.exists("Workflow", {"workflow_name":name}):
            continue  # preserve administrator changes
        roles=mappings.get(dt) or {"owner":"System Manager","reviewer":"System Manager","approver":"System Manager"}
        states=[]
        for state in spec["states"]:
            role=roles["owner"] if state in ("Draft","Rejected") else (roles["reviewer"] if state in ("Submitted","Under Review") else roles["approver"])
            states.append({"state":state,"doc_status":0,"allow_edit":role})
        frappe.get_doc({
            "doctype":"Workflow","workflow_name":name,"document_type":dt,
            "is_active":1,"workflow_state_field":"workflow_state","send_email_alert":0,
            "states":states,"transitions":_transitions(spec["states"],roles),
        }).insert(ignore_permissions=True)
    frappe.clear_cache()
