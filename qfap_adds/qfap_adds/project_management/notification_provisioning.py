from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

RULES = {
    "critical_risk": ("Critical Project Risk", "Project Risk", "On Save", 0, "A High or Critical project risk requires attention."),
    "risk_review_overdue": ("Risk Review Overdue", "Project Risk", "Daily", 7, "A project risk review date is due or overdue."),
    "deliverable_due_soon": ("Compliance Deliverable Due Soon", "Project Compliance Deliverable", "Daily", 7, "A compliance deliverable is approaching its submission due date."),
    "deliverable_overdue": ("Compliance Deliverable Overdue", "Project Compliance Deliverable", "Daily", 0, "A compliance deliverable has passed its due date without completion."),
    "change_pending_implementation": ("Approved Change Pending Implementation", "Project Change Request", "Daily", 7, "An approved change remains pending implementation."),
    "closure_action_overdue": ("Closure Action Overdue", "Project Closure", "Daily", 7, "A project closure action is overdue."),
    "progress_update_overdue": ("Project Progress Update Overdue", "Project Progress Update", "Daily", 7, "A required project progress update is overdue."),
}

CHILD_FIELDS = [
    {"fieldname":"rule_label","label":"Rule Label","fieldtype":"Data","read_only":1,"in_list_view":1,"insert_after":"notification_key"},
    {"fieldname":"description","label":"Description","fieldtype":"Small Text","read_only":1,"insert_after":"rule_label"},
    {"fieldname":"reference_doctype","label":"Reference DocType","fieldtype":"Link","options":"DocType","read_only":1,"in_list_view":1,"insert_after":"description"},
    {"fieldname":"trigger_type","label":"Trigger Type","fieldtype":"Select","options":"On Save\nDaily","read_only":1,"in_list_view":1,"insert_after":"reference_doctype"},
    {"fieldname":"delivery_channel","label":"Delivery Channel","fieldtype":"Select","options":"System Notification\nEmail and System Notification","default":"System Notification","in_list_view":1,"insert_after":"trigger_type"},
    {"fieldname":"fallback_to_project_manager","label":"Fallback to Project Manager","fieldtype":"Check","default":"1","insert_after":"recipient_employee"},
    {"fieldname":"notification_record","label":"Notification Template","fieldtype":"Link","options":"Notification","read_only":1,"insert_after":"fallback_to_project_manager"},
]

SETTINGS_HELP = [
    {"fieldname":"custom_project_notification_help","label":"How Project Notifications Work","fieldtype":"HTML","options":"<div class='alert alert-info'><b>Project notifications are active policies.</b> Enable a rule, choose a Recipient Role or Recipient Employee, and set the delivery channel. Due Soon Days is used by scheduled rules. The linked Notification Template controls the editable subject and message. If no recipient is configured, the engine may fall back to the Project Manager when enabled.</div>","insert_after":"custom_project_notification_rules_section"},
]


def _ensure_template(key, label, doctype, description):
    name="QFAP - "+label
    if frappe.db.exists("Notification",name):
        return name
    meta=frappe.get_meta("Notification")
    data={
        "doctype":"Notification","name":name,"subject":label+" - {{ doc.name }}",
        "document_type":doctype,"event":"Save","enabled":0,
        "condition":"False",
        "message":"<p>"+description+"</p><p><b>Document:</b> {{ doc.name }}</p><p><b>Project:</b> {{ doc.project or '' }}</p>",
        "channel":"System Notification",
    }
    data={k:v for k,v in data.items() if k in ("doctype","name") or meta.has_field(k)}
    doc=frappe.get_doc(data)
    if doc.meta.has_field("recipients"):
        doc.append("recipients",{"receiver_by_role":"System Manager"})
    doc.insert(ignore_permissions=True)
    return name


def provision_project_notifications():
    if not frappe.db.exists("DocType","Project Notification Rule"):
        return
    create_custom_fields({"Project Notification Rule":CHILD_FIELDS,"Projects Settings":SETTINGS_HELP},update=True)
    settings=frappe.get_single("Projects Settings")
    existing={row.notification_key:row for row in settings.get("project_notification_rules") or []}
    for key, spec in RULES.items():
        label, doctype, trigger, days, description=spec
        row=existing.get(key)
        if not row:
            row=settings.append("project_notification_rules",{"notification_key":key,"enabled":1,"due_soon_days":days})
        row.rule_label=label
        row.description=description
        row.reference_doctype=doctype if frappe.db.exists("DocType",doctype) else ""
        row.trigger_type=trigger
        if not row.delivery_channel: row.delivery_channel="System Notification"
        row.fallback_to_project_manager=1 if row.get("fallback_to_project_manager") is None else row.fallback_to_project_manager
        if frappe.db.exists("DocType",doctype): row.notification_record=_ensure_template(key,label,doctype,description)
    settings.save(ignore_permissions=True)
    frappe.clear_cache(doctype="Projects Settings")
