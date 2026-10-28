from __future__ import annotations

import frappe
from frappe import _

RESPONSIBLE_FIELD = "custom_current_responsible_user"
BYPASS_ROLES = {"System Manager", "Workflow Admin"}


def validate_responsible_user(doc, method=None):
    """Allow edits only by the responsibility owner stored before this save.

    The database value is authoritative. This permits the existing owner to hand
    the document to the next owner in the same save, while blocking later edits
    by the former owner after the handoff has completed.
    """
    if not doc.meta.has_field(RESPONSIBLE_FIELD):
        return

    if doc.is_new():
        if not getattr(doc.flags, "qfap_allow_initial_responsible_user", False):
            doc.set(RESPONSIBLE_FIELD, None)
        return

    if _must_bypass(doc) or not _has_active_workflow(doc.doctype):
        return

    current_user = frappe.session.user
    stored_responsible = _clean(
        frappe.db.get_value(doc.doctype, doc.name, RESPONSIBLE_FIELD)
    )
    incoming_responsible = _clean(doc.get(RESPONSIBLE_FIELD))

    if not stored_responsible and not incoming_responsible:
        return
    if stored_responsible == current_user:
        return

    # The atomic workflow service sets this server-only flag only after it has
    # validated the document, transition, current owner, next user, and role.
    # It covers the first assignment and the same-save handoff without opening a
    # general bypass for browser saves, imports, or direct field manipulation.
    if getattr(doc.flags, "qfap_atomic_workflow_handoff", False):
        return

    if not stored_responsible and incoming_responsible == current_user:
        return

    frappe.throw(
        _(
            "Only the current responsible user can modify this workflow "
            "document. Current responsible user: {0}"
        ).format(stored_responsible or incoming_responsible),
        frappe.PermissionError,
    )


def can_override_responsibility(user=None):
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    return bool(BYPASS_ROLES.intersection(frappe.get_roles(user)))


def _must_bypass(doc):
    if frappe.flags.in_install or frappe.flags.in_migrate:
        return True
    if getattr(doc.flags, "ignore_permissions", False):
        return True
    return can_override_responsibility()


def _has_active_workflow(doctype):
    return bool(
        frappe.db.exists(
            "Workflow",
            {"document_type": doctype, "is_active": 1},
        )
    )


def _clean(value):
    return str(value or "").strip()
