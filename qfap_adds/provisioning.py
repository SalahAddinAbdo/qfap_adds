from __future__ import annotations

from pathlib import Path

import frappe


PRINT_FORMAT_PREFIX = "QFAP Universal - "
EXCLUDED_MODULES = {"Core", "Desk", "Email", "Geo", "Integrations", "Printing", "Social", "Website"}


def provision_universal_print_formats():
    """Create or update one managed Jinja Print Format per submittable DocType."""
    template = Path(__file__).parent / "templates" / "universal_dynamic_print_format.html"
    html = template.read_text(encoding="utf-8")
    doctypes = frappe.get_all(
        "DocType",
        filters={"istable": 0, "issingle": 0, "is_virtual": 0, "is_submittable": 1},
        fields=["name", "module"],
        order_by="name asc",
        limit_page_length=0,
    )
    for row in doctypes:
        if row.module not in EXCLUDED_MODULES:
            _upsert_print_format(row.name, html)
    frappe.clear_cache(doctype="Print Format")


def _upsert_print_format(doctype, html):
    name = PRINT_FORMAT_PREFIX + doctype
    values = {
        "doc_type": doctype,
        "print_format_type": "Jinja",
        "custom_format": 1,
        "disabled": 0,
        "html": html,
        "module": "QFap Adds",
        "standard": "No",
    }
    if frappe.db.exists("Print Format", name):
        doc = frappe.get_doc("Print Format", name)
        for fieldname, value in values.items():
            doc.set(fieldname, value)
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc({"doctype": "Print Format", "name": name, **values}).insert(ignore_permissions=True)
    frappe.db.set_value("DocType", doctype, "default_print_format", name, update_modified=False)
