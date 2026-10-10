from __future__ import annotations

import frappe
from frappe import _

RESPONSIBLE_FIELD = "custom_current_responsible_user"
BYPASS_ROLES = {"System Manager", "Workflow Admin"}


def validate_responsible_user(doc, method=None):
    """Protect workflow documents without blocking migrations or valid transitions.

    The database value is authoritative. A valid transition may change the field
    from the current user to the next responsible user in the same save.
    """
    if _must_bypass(doc):
        return
    if not doc.meta.has_field(RESPONSIBLE_FIELD):
        return
    if not _has_active_workflow(doc.doctype):
        return

    current_user = frappe.session.user
    stored_responsible = frappe.db.get_value(doc.doctype, doc.name, RESPONSIBLE_FIELD)
    incoming_responsible = doc.get(RESPONSIBLE_FIELD)

    # No responsibility has been assigned yet.
    if not stored_responsible and not incoming_responsible:
        return

    # The user who owned the document before this save may execute a valid
    # workflow transition and hand responsibility to the next user.
    if stored_responsible == current_user:
        return

    # The assigned user may edit when the stored field was not yet populated,
    # for example immediately after field provisioning or legacy migration.
    if not stored_responsible and incoming_responsible == current_user:
        return

    frappe.throw(
        _("Only the current responsible user can modify this workflow document. Current responsible user: {0}").format(
            stored_responsible or incoming_responsible
        ),
        frappe.PermissionError,
    )


def _must_bypass(doc):
    if doc.is_new():
        return True
    if frappe.session.user in {"Administrator", "Guest"}:
        return frappe.session.user == "Administrator"
    if BYPASS_ROLES.intersection(frappe.get_roles(frappe.session.user)):
        return True
    if getattr(frappe.flags, "in_migrate", False):
        return True
    if getattr(frappe.flags, "in_install", False):
        return True
    if getattr(frappe.flags, "in_patch", False):
        return True
    if getattr(doc.flags, "ignore_permissions", False):
        return True
    if getattr(doc.flags, "ignore_validate", False):
        return True
    return False


def _has_active_workflow(doctype):
    cache_key = "qfap_active_workflow::" + doctype
    cached = frappe.cache.get_value(cache_key)
    if cached is not None:
        return bool(cached)
    exists = bool(frappe.db.exists("Workflow", {"document_type": doctype, "is_active": 1}))
    frappe.cache.set_value(cache_key, 1 if exists else 0, expires_in_sec=300)
    return exists
