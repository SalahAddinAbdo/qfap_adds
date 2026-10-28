from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.model.docstatus import DocStatus
from frappe.model.workflow import (
    WorkflowTransitionError,
    get_transitions,
    get_workflow,
    has_approval_access,
)
from frappe.utils import cint, get_datetime

from qfap_adds.qfap_adds.api.signatures import apply_signature_values
from qfap_adds.qfap_adds.workflow.permissions import (
    RESPONSIBLE_FIELD,
    can_override_responsibility,
)

MAX_COMMENT_LENGTH = 10000
DEFAULT_WORKFLOW_TASKS = {"Webhook", "Server Script"}


@frappe.whitelist()
def apply_assigned_workflow_action(
    doctype: str,
    document_name: str,
    action: str,
    next_user: str | None = None,
    signature_notes: str | None = None,
    internal_comment: str | None = None,
    expected_modified: str | None = None,
) -> dict[str, Any]:
    """Execute a workflow action, signature, assignment, and comments atomically.

    No explicit commit or rollback is used. Frappe commits the request only after
    this method returns successfully and rolls the entire request back when any
    validation or save operation raises an exception.
    """
    doctype = _clean_required(doctype, _("Document Type"))
    document_name = _clean_required(document_name, _("Document Name"))
    action = _clean_required(action, _("Workflow Action"))
    next_user = _clean(next_user)
    signature_notes = _clean(signature_notes)
    internal_comment = _clean(internal_comment)

    if len(internal_comment) > MAX_COMMENT_LENGTH:
        frappe.throw(
            _("Internal Comment cannot exceed {0} characters.").format(
                MAX_COMMENT_LENGTH
            )
        )

    meta = frappe.get_meta(doctype)
    if meta.issingle:
        frappe.throw(_("Workflow handoff is not supported for Single DocTypes."))

    _lock_document(doctype, document_name)
    doc = frappe.get_doc(doctype, document_name)

    _validate_expected_version(doc, expected_modified)
    _validate_document_access(doc)
    _validate_current_responsible_user(doc)

    transition = _get_allowed_transition(doc, action)

    # Server-only trust marker. It permits the validated atomic workflow service
    # to perform the first assignment or a handoff in the same save. This flag is
    # not a document field and cannot be supplied by the browser as document data.
    doc.flags.qfap_atomic_workflow_handoff = True

    assignment = _prepare_assignment(doc, transition, next_user)
    signature_result = _prepare_signature(
        doc,
        transition,
        signature_notes=signature_notes,
    )

    # Assignment and signature values remain on the same in-memory document.
    # The workflow state and docstatus are then applied by one synchronous save,
    # submit, or cancel operation. No intermediate document save is performed.
    updated_doc = _apply_workflow_transition(doc, transition)

    if signature_result.get("comment"):
        updated_doc.add_comment("Info", signature_result["comment"])

    if internal_comment:
        updated_doc.add_comment("Comment", frappe.utils.escape_html(internal_comment))

    return {
        "doc": updated_doc.as_dict(),
        "action": action,
        "workflow_state": updated_doc.get("workflow_state"),
        "assigned": assignment["assigned"],
        "next_user": assignment["next_user"],
        "signature": {
            key: value
            for key, value in signature_result.items()
            if key != "comment"
        },
        "comment_recorded": bool(internal_comment),
    }


def _apply_workflow_transition(doc, transition):
    """Apply the validated transition without reloading away pending field values."""
    workflow = get_workflow(doc.doctype)

    if not has_approval_access(frappe.session.user, doc, transition):
        frappe.throw(_("Self approval is not allowed."), frappe.PermissionError)

    next_state = next(
        (row for row in workflow.states if row.state == transition.next_state),
        None,
    )
    if not next_state:
        frappe.throw(
            _("Workflow next state does not exist: {0}").format(
                frappe.bold(transition.next_state)
            ),
            WorkflowTransitionError,
        )

    doc.set(workflow.workflow_state_field, transition.next_state)
    if next_state.update_field:
        doc.set(next_state.update_field, next_state.update_value)

    _run_transition_tasks(doc, transition)

    target_status = DocStatus(next_state.doc_status or 0)
    if doc.docstatus.is_draft() and target_status.is_draft():
        doc.save()
    elif doc.docstatus.is_draft() and target_status.is_submitted():
        # The atomic handoff must finish in the current request. It deliberately
        # submits synchronously even when the DocType normally queues submission.
        doc.submit()
    elif doc.docstatus.is_submitted() and target_status.is_submitted():
        doc.save()
    elif doc.docstatus.is_submitted() and target_status.is_cancelled():
        doc.cancel()
    else:
        frappe.throw(
            _("Illegal Document Status for workflow state {0}.").format(
                frappe.bold(next_state.state)
            ),
            WorkflowTransitionError,
        )

    doc.add_comment("Workflow", _(next_state.state))
    return doc


def _run_transition_tasks(doc, transition) -> None:
    task_group = transition.get("transition_tasks")
    if not task_group:
        return
    if not frappe.db.exists("DocType", "Workflow Transition Task"):
        frappe.throw(
            _("Workflow Transition Tasks are configured but unavailable on this site.")
        )

    rows = frappe.db.get_all(
        "Workflow Transition Task",
        {"parent": task_group, "enabled": 1},
        ["task", "link", "asynchronous"],
        order_by="idx",
    )
    registered = {
        item["name"]: item["method"]
        for item in frappe.get_hooks("workflow_methods")
    }

    for row in rows:
        method = _resolve_transition_task(row, registered)
        if cint(row.asynchronous):
            frappe.enqueue(method, doc=doc, enqueue_after_commit=True)
        else:
            method(doc)


def _resolve_transition_task(row, registered):
    if row.task in DEFAULT_WORKFLOW_TASKS:
        if row.task == "Webhook":
            return frappe.get_doc("Webhook", row.link).execute_for_doc
        if row.task == "Server Script":
            return frappe.get_doc("Server Script", row.link).execute_workflow_task

    method_path = registered.get(row.task)
    if not method_path:
        frappe.throw(_('There is no workflow task called "{0}".').format(row.task))
    return frappe.get_attr(method_path)


def _get_allowed_transition(doc, action: str):
    transitions = get_transitions(doc) or []
    matches = [
        transition
        for transition in transitions
        if _clean(transition.get("action")) == action
    ]
    if not matches:
        frappe.throw(
            _("Action {0} is not allowed from the current workflow state.").format(
                frappe.bold(action)
            ),
            frappe.PermissionError,
        )
    if len(matches) > 1:
        frappe.throw(
            _(
                "Workflow configuration contains more than one allowed transition "
                "for action {0} from the current state."
            ).format(frappe.bold(action))
        )
    return matches[0]


def _prepare_assignment(doc, transition, next_user: str) -> dict[str, Any]:
    assignment_required = cint(transition.get("custom_assignment_required")) == 1
    target_field = _clean(transition.get("custom_target_user_field"))
    target_role = _clean(transition.get("custom_target_role"))

    if assignment_required and not next_user:
        frappe.throw(_("The next responsible user is required for this action."))

    if not next_user:
        return {"assigned": False, "next_user": "", "target_field": target_field}

    if not target_field:
        frappe.throw(
            _("Target User Field is not configured for workflow action {0}.").format(
                frappe.bold(transition.get("action"))
            )
        )
    if not doc.meta.has_field(target_field):
        frappe.throw(
            _("Configured Target User Field does not exist in {0}: {1}").format(
                frappe.bold(doc.doctype),
                frappe.bold(target_field),
            )
        )
    if not doc.meta.has_field(RESPONSIBLE_FIELD):
        frappe.throw(
            _("Required workflow responsibility field is missing: {0}").format(
                frappe.bold(RESPONSIBLE_FIELD)
            )
        )

    _validate_next_user(next_user, target_role)
    doc.set(target_field, next_user)
    doc.set(RESPONSIBLE_FIELD, next_user)

    return {
        "assigned": True,
        "next_user": next_user,
        "target_field": target_field,
    }


def _prepare_signature(doc, transition, signature_notes: str) -> dict[str, Any]:
    if cint(transition.get("custom_apply_employee_signature")) != 1:
        return {"signed": False, "already_signed": False}

    mapping_key = _clean(
        transition.get("custom_employee_signature_mapping_key")
    )
    if not mapping_key:
        frappe.throw(
            _("Employee Signature Mapping is missing for workflow action {0}.").format(
                frappe.bold(transition.get("action"))
            )
        )

    return apply_signature_values(
        doc,
        mapping_key=mapping_key,
        signature_notes=signature_notes,
        user=frappe.session.user,
    )


def _validate_next_user(user: str, required_role: str) -> None:
    enabled = frappe.db.get_value("User", user, "enabled")
    if enabled is None:
        frappe.throw(_("Selected next responsible user does not exist: {0}").format(user))
    if not cint(enabled):
        frappe.throw(_("Selected next responsible user is disabled: {0}").format(user))

    if required_role and not frappe.db.exists(
        "Has Role",
        {"parent": user, "parenttype": "User", "role": required_role},
    ):
        frappe.throw(
            _("Selected user {0} does not have the required role {1}.").format(
                frappe.bold(user),
                frappe.bold(required_role),
            )
        )


def _validate_document_access(doc) -> None:
    if not frappe.has_permission(doc.doctype, "read", doc.name):
        frappe.throw(
            _("You do not have permission to read this document."),
            frappe.PermissionError,
        )


def _validate_current_responsible_user(doc) -> None:
    if not doc.meta.has_field(RESPONSIBLE_FIELD):
        return
    if can_override_responsibility():
        return

    responsible = _clean(doc.get(RESPONSIBLE_FIELD))
    if responsible and responsible != frappe.session.user:
        frappe.throw(
            _(
                "Only the current responsible user can perform this workflow "
                "action. Current responsible user: {0}"
            ).format(responsible),
            frappe.PermissionError,
        )


def _validate_expected_version(doc, expected_modified: str | None) -> None:
    expected_modified = _clean(expected_modified)
    if not expected_modified:
        return
    if get_datetime(expected_modified) != get_datetime(doc.modified):
        frappe.throw(
            _(
                "This document was modified after it was opened. Reload the "
                "document and repeat the workflow action."
            ),
            frappe.TimestampMismatchError,
        )


def _lock_document(doctype: str, document_name: str) -> None:
    table = "tab" + doctype.replace("`", "``")
    rows = frappe.db.sql(
        f"select name from `{table}` where name = %s for update",
        (document_name,),
    )
    if not rows:
        frappe.throw(
            _("Document {0} {1} does not exist.").format(
                frappe.bold(doctype),
                frappe.bold(document_name),
            ),
            frappe.DoesNotExistError,
        )


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _clean_required(value: Any, label: str) -> str:
    value = _clean(value)
    if not value:
        frappe.throw(_("{0} is required.").format(label))
    return value
