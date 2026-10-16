from __future__ import annotations

import json
from pathlib import Path

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

BASE = Path(__file__).resolve().parent

ADMIN_ROLE = "Task Management Administrator"
REPORT_ROLE = "Reports Viewer"
DEFAULT_SUMMARY_EMAIL_TEMPLATE = "Farabi Task Summary"
WORKFLOW_NAME = "Task Assignment Request Approval"
WORKFLOW_DOCTYPE = "Task Assignment Request"

WORKFLOW_STATES = (
    ("Draft", "Inverse"),
    ("Pending Approval", "Warning"),
    ("Approved", "Info"),
    ("Rejected", "Danger"),
    ("Applied", "Success"),
    ("Application Failed", "Danger"),
)

WORKFLOW_ACTIONS = (
    "Submit for Approval",
    "Approve",
    "Reject",
)

SETTINGS_DEFAULTS = {
    "enabled": 1,
    "hierarchy_max_depth": 100,
    "administrative_role": ADMIN_ROLE,
    "global_reopen_roles": f"System Manager\n{ADMIN_ROLE}",
    "allow_unassigned_standard_tasks": 1,
    "allow_workplan_as_parent": 1,
    "exclude_locked_parents": 1,
    "parent_must_same_project": 1,
    "weekly_summary_enabled": 1,
    "warn_legacy_scripts": 1,
}


def _load_json(filename: str):
    path = BASE / filename
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _ensure_role(role_name: str) -> None:
    if not role_name or frappe.db.exists("Role", role_name):
        return

    frappe.get_doc(
        {
            "doctype": "Role",
            "role_name": role_name,
            "desk_access": 1,
        }
    ).insert(ignore_permissions=True)


def _ensure_notification(data: dict) -> None:
    # Preserve administrator changes. Provision only records that do not exist.
    if not frappe.db.exists("Notification", data["name"]):
        frappe.get_doc(data).insert(ignore_permissions=True)



def _ensure_task_summary_email_template() -> None:
    """Create the editable default template once and preserve later user changes."""
    if not frappe.db.exists("DocType", "Email Template"):
        return

    template_data = _load_json("task_summary_email_template.json")
    template_name = template_data["name"]

    if not frappe.db.exists("Email Template", template_name):
        frappe.get_doc(
            {
                "doctype": "Email Template",
                "name": template_name,
                "subject": template_data["subject"],
                "use_html": int(template_data.get("use_html") or 1),
                "response_html": template_data["response_html"],
            }
        ).insert(ignore_permissions=True)

    if frappe.db.exists("DocType", "Task Management Settings"):
        current = frappe.db.get_single_value(
            "Task Management Settings", "summary_email_template"
        )
        use_new_template = not current
        if current == "Farabi Task Summary" and frappe.db.exists("Email Template", current):
            current_body = frappe.db.get_value(
                "Email Template", current, "response_html"
            ) or ""
            # Switch only when the previous template is still the original wrapper.
            # A customized legacy template remains selected and untouched.
            use_new_template = (
                "generated_summary_html" in current_body
                and len(current_body.strip()) < 1500
            )
        if use_new_template:
            frappe.db.set_single_value(
                "Task Management Settings",
                "summary_email_template",
                template_name,
            )


def _ensure_workflow_state(state_name: str, style: str) -> None:
    existing_name = frappe.db.get_value(
        "Workflow State",
        {"workflow_state_name": state_name},
        "name",
    )

    if existing_name:
        return

    frappe.get_doc(
        {
            "doctype": "Workflow State",
            "workflow_state_name": state_name,
            "style": style,
        }
    ).insert(ignore_permissions=True)


def _ensure_workflow_action(action_name: str) -> None:
    existing_name = frappe.db.get_value(
        "Workflow Action Master",
        {"workflow_action_name": action_name},
        "name",
    )

    if existing_name:
        return

    frappe.get_doc(
        {
            "doctype": "Workflow Action Master",
            "workflow_action_name": action_name,
        }
    ).insert(ignore_permissions=True)


def _workflow_definition() -> dict:
    return {
        "doctype": "Workflow",
        "workflow_name": WORKFLOW_NAME,
        "document_type": WORKFLOW_DOCTYPE,
        "is_active": 1,
        "workflow_state_field": "workflow_state",
        "send_email_alert": 0,
        "states": [
            {
                "state": "Draft",
                "doc_status": 0,
                "allow_edit": "Employee",
            },
            {
                "state": "Pending Approval",
                "doc_status": 0,
                "allow_edit": ADMIN_ROLE,
            },
            {
                "state": "Approved",
                "doc_status": 0,
                "allow_edit": ADMIN_ROLE,
            },
            {
                "state": "Rejected",
                "doc_status": 0,
                "allow_edit": ADMIN_ROLE,
            },
            {
                "state": "Applied",
                "doc_status": 0,
                "allow_edit": ADMIN_ROLE,
            },
            {
                "state": "Application Failed",
                "doc_status": 0,
                "allow_edit": ADMIN_ROLE,
            },
        ],
        "transitions": [
            {
                "state": "Draft",
                "action": "Submit for Approval",
                "next_state": "Pending Approval",
                "allowed": "Employee",
            },
            {
                "state": "Pending Approval",
                "action": "Approve",
                "next_state": "Approved",
                "allowed": "Employee",
            },
            {
                "state": "Pending Approval",
                "action": "Reject",
                "next_state": "Rejected",
                "allowed": "Employee",
            },
        ],
    }


def _ensure_workflow() -> None:
    if not frappe.db.exists("DocType", WORKFLOW_DOCTYPE):
        frappe.throw(
            f"DocType {WORKFLOW_DOCTYPE} must exist before provisioning its Workflow."
        )

    for state_name, style in WORKFLOW_STATES:
        _ensure_workflow_state(state_name, style)

    # Workflow Transition.action is a Link to Workflow Action Master.
    # These records must exist before inserting or updating the Workflow.
    for action_name in WORKFLOW_ACTIONS:
        _ensure_workflow_action(action_name)

    definition = _workflow_definition()
    existing_name = frappe.db.get_value(
        "Workflow",
        {"workflow_name": WORKFLOW_NAME},
        "name",
    )

    if existing_name:
        # Preserve administrator changes to states and transitions.
        return

    frappe.get_doc(definition).insert(ignore_permissions=True)


def _create_or_update_task_custom_fields() -> None:
    grouped_fields = {}

    for item in _load_json("task_custom_fields.json"):
        doctype = item["dt"]
        field_definition = {
            key: value
            for key, value in item.items()
            if key not in ("doctype", "name", "dt")
        }
        grouped_fields.setdefault(doctype, []).append(field_definition)

    create_custom_fields(grouped_fields, update=True)


def _configure_task_properties() -> None:
    make_property_setter(
        "Task",
        None,
        "track_changes",
        1,
        "Check",
        validate_fields_for_doctype=False,
    )
    make_property_setter(
        "Task",
        None,
        "quick_entry",
        0,
        "Check",
        validate_fields_for_doctype=False,
    )


def _provision_notifications() -> None:
    for notification in _load_json("notifications.json"):
        _ensure_notification(notification)


def _set_task_management_defaults() -> None:
    if not frappe.db.exists("DocType", "Task Management Settings"):
        return

    settings_meta = frappe.get_meta("Task Management Settings")

    for fieldname, value in SETTINGS_DEFAULTS.items():
        if not settings_meta.has_field(fieldname):
            continue

        current_value = frappe.db.get_single_value(
            "Task Management Settings",
            fieldname,
        )

        if current_value in (None, ""):
            frappe.db.set_single_value(
                "Task Management Settings",
                fieldname,
                value,
            )


def provision_task_integration() -> None:
    """Provision Task Management configuration in an idempotent order."""

    _ensure_role(ADMIN_ROLE)
    _ensure_role(REPORT_ROLE)

    _create_or_update_task_custom_fields()
    _configure_task_properties()
    _provision_notifications()
    _ensure_task_summary_email_template()
    _set_task_management_defaults()
    _ensure_workflow()

    for doctype in (
        "Task",
        "Task Management Settings",
        "Task Assignment Request",
        "QFAP Managed Task Share",
        "Workflow",
    ):
        if frappe.db.exists("DocType", doctype):
            frappe.clear_cache(doctype=doctype)
