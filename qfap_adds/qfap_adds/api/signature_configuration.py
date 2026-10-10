from __future__ import annotations

import frappe
from frappe import _


@frappe.whitelist()
def provision_fields(configuration):
    if not frappe.has_permission("Employee Signature Configuration", "write", configuration):
        frappe.throw(_("You do not have permission to update this configuration."), frappe.PermissionError)
    doc = frappe.get_doc("Employee Signature Configuration", configuration)
    doc.run_method("validate")
    from qfap_adds.qfap_adds.signatures.provisioning import provision_signature_fields
    provision_signature_fields(doc)
    return {"created": True, "document_type": doc.document_type}
