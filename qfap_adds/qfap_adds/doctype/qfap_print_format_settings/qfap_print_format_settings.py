import frappe
from frappe import _
from frappe.model.document import Document


ALLOWED_PROFILES = {"QFAP Universal"}


class QFAPPrintFormatSettings(Document):
    def validate(self):
        seen = set()
        for row in self.rules or []:
            if not row.document_type:
                frappe.throw(_("Document Type is required in row {0}.").format(row.idx))
            if row.document_type in seen:
                frappe.throw(_("Document Type {0} is duplicated in row {1}.").format(row.document_type, row.idx))
            seen.add(row.document_type)
            _validate_document_type(row.document_type, row.idx)
            if row.print_profile not in ALLOWED_PROFILES:
                frappe.throw(_("Unsupported Print Profile in row {0}: {1}").format(row.idx, row.print_profile))

    def on_update(self):
        frappe.enqueue(
            "qfap_adds.printing.provisioning.provision_universal_print_formats",
            queue="short",
            enqueue_after_commit=True,
        )


def _validate_document_type(doctype, row_number):
    if not frappe.db.exists("DocType", doctype):
        frappe.throw(_("Document Type {0} in row {1} does not exist.").format(doctype, row_number))

    values = frappe.db.get_value(
        "DocType",
        doctype,
        ["istable", "issingle", "is_virtual"],
        as_dict=True,
    )
    if values.istable:
        frappe.throw(_("Child Table {0} cannot be used in row {1}.").format(doctype, row_number))
    if values.issingle:
        frappe.throw(_("Single/Settings DocType {0} cannot be used in row {1}.").format(doctype, row_number))
    if values.is_virtual:
        frappe.throw(_("Virtual DocType {0} cannot be used in row {1}.").format(doctype, row_number))
