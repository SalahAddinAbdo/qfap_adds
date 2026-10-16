from __future__ import annotations

import json
from pathlib import Path

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

BASE = Path(__file__).resolve().parent


def _load(name):
    with open(BASE / name, encoding="utf-8") as handle:
        return json.load(handle)


def _ensure_role(role_name):
    if role_name and not frappe.db.exists("Role", role_name):
        frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(ignore_permissions=True)


def _upsert_notification(data):
    name = data["name"]
    if frappe.db.exists("Notification", name):
        doc = frappe.get_doc("Notification", name)
        doc.update({k: v for k, v in data.items() if k not in ("doctype", "name", "recipients")})
        doc.set("recipients", data.get("recipients") or [])
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc(data).insert(ignore_permissions=True)


def _ensure_workflow():
    states=[("Draft","Inverse"),("Pending Approval","Warning"),("Approved","Info"),("Rejected","Danger"),("Applied","Success"),("Application Failed","Danger")]
    for state,color in states:
        if not frappe.db.exists("Workflow State",state):frappe.get_doc({"doctype":"Workflow State","workflow_state_name":state,"style":color}).insert(ignore_permissions=True)
    name="Task Assignment Request Approval"
    data={"doctype":"Workflow","workflow_name":name,"document_type":"Task Assignment Request","is_active":1,"workflow_state_field":"workflow_state","send_email_alert":0,"states":[{"state":"Draft","doc_status":"0","allow_edit":"Employee"},{"state":"Pending Approval","doc_status":"0","allow_edit":"Task Management Administrator"},{"state":"Approved","doc_status":"0","allow_edit":"Task Management Administrator"},{"state":"Rejected","doc_status":"0","allow_edit":"Task Management Administrator"},{"state":"Applied","doc_status":"0","allow_edit":"Task Management Administrator"},{"state":"Application Failed","doc_status":"0","allow_edit":"Task Management Administrator"}],"transitions":[{"state":"Draft","action":"Submit for Approval","next_state":"Pending Approval","allowed":"Employee"},{"state":"Pending Approval","action":"Approve","next_state":"Approved","allowed":"Employee"},{"state":"Pending Approval","action":"Reject","next_state":"Rejected","allowed":"Employee"}]}
    if frappe.db.exists("Workflow",name):
        doc=frappe.get_doc("Workflow",name); doc.update({k:v for k,v in data.items() if k not in ("doctype","workflow_name","states","transitions")}); doc.set("states",data["states"]); doc.set("transitions",data["transitions"]); doc.save(ignore_permissions=True)
    else:frappe.get_doc(data).insert(ignore_permissions=True)

def provision_task_integration():
    _ensure_role("Task Management Administrator")
    _ensure_role("Reports Viewer")
    # Idempotent: update by dt/fieldname and never create duplicate fields.
    grouped = {}
    for item in _load("task_custom_fields.json"):
        dt = item["dt"]
        field = {k: v for k, v in item.items() if k not in ("doctype", "name", "dt")}
        grouped.setdefault(dt, []).append(field)
    create_custom_fields(grouped, update=True)

    # Stable Task behavior across sites; updates existing Property Setters by key.
    make_property_setter("Task", None, "track_changes", 1, "Check", validate_fields_for_doctype=False)
    make_property_setter("Task", None, "quick_entry", 0, "Check", validate_fields_for_doctype=False)

    for notification in _load("notifications.json"):
        _upsert_notification(notification)

    # Insert defaults only when the Single DocType has no explicit values.
    if frappe.db.exists("DocType", "Task Management Settings"):
        defaults = {"enabled": 1, "hierarchy_max_depth": 100,
                    "administrative_role": "Task Management Administrator",
                    "global_reopen_roles": "System Manager\nTask Management Administrator",
                    "allow_unassigned_standard_tasks": 1,
                    "allow_workplan_as_parent": 1, "exclude_locked_parents": 1,
                    "parent_must_same_project": 1, "weekly_summary_enabled": 1,
                    "warn_legacy_scripts": 1}
        for fieldname, value in defaults.items():
            if frappe.db.get_single_value("Task Management Settings", fieldname) in (None, ""):
                frappe.db.set_single_value("Task Management Settings", fieldname, value)

    _ensure_workflow()
    frappe.clear_cache(doctype="Task")
    frappe.clear_cache(doctype="Task Management Settings")
