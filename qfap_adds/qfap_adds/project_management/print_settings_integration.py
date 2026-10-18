from __future__ import annotations
import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

FIELDS={"Print Settings":[
 {"fieldname":"qorg_print_section","label":"Q Org Print Configuration","fieldtype":"Section Break","insert_after":"print_style"},
 {"fieldname":"qorg_rules","label":"Managed Print Format Rules","fieldtype":"Table","options":"QFAP Print Format Rule","insert_after":"qorg_print_section","description":"Enabled rows receive the managed Q Org universal print format."},
 {"fieldname":"qorg_apply_formats","label":"Apply Managed Print Formats","fieldtype":"Button","insert_after":"qorg_rules"},
 {"fieldname":"qorg_sync_column","fieldtype":"Column Break","insert_after":"qorg_apply_formats"},
 {"fieldname":"qorg_last_sync_on","label":"Last Sync On","fieldtype":"Datetime","read_only":1,"insert_after":"qorg_sync_column"},
 {"fieldname":"qorg_last_sync_summary","label":"Last Sync Summary","fieldtype":"Small Text","read_only":1,"insert_after":"qorg_last_sync_on"},
 {"fieldname":"qorg_managed_once","label":"Managed Once","fieldtype":"Check","hidden":1,"read_only":1,"default":"0","insert_after":"qorg_last_sync_summary"},
]}
def provision_print_settings():
    create_custom_fields(FIELDS,update=True)
    _migrate_legacy_values()
def _migrate_legacy_values():
    if not frappe.db.exists("DocType","QFAP Print Format Settings"): return
    old=frappe.get_single("QFAP Print Format Settings"); new=frappe.get_single("Print Settings")
    if not new.get("qorg_rules") and old.get("rules"):
        for row in old.rules: new.append("qorg_rules",{k:v for k,v in row.as_dict().items() if k not in ("name","parent","parenttype","parentfield","doctype","idx")})
    new.qorg_last_sync_on=old.get("last_sync_on"); new.qorg_last_sync_summary=old.get("last_sync_summary"); new.qorg_managed_once=old.get("managed_once")
    new.flags.ignore_validate=True; new.save(ignore_permissions=True)
def validate_print_settings(doc,method=None):
    seen=set()
    for row in doc.get("qorg_rules") or []:
        if not row.get("document_type"): frappe.throw(_("Document Type is required in row {0}.").format(row.idx))
        if row.document_type in seen: frappe.throw(_("Document Type {0} is duplicated.").format(row.document_type))
        seen.add(row.document_type)
def sync_print_settings(doc=None,method=None):
    if not frappe.db.exists("DocType","QFAP Print Format Settings"): return
    source=doc or frappe.get_single("Print Settings"); legacy=frappe.get_single("QFAP Print Format Settings"); legacy.set("rules",[])
    for row in source.get("qorg_rules") or []: legacy.append("rules",{k:v for k,v in row.as_dict().items() if k not in ("name","parent","parenttype","parentfield","doctype","idx")})
    legacy.flags.ignore_validate=True; legacy.flags.ignore_on_update=True; legacy.save(ignore_permissions=True)
@frappe.whitelist()
def apply_print_formats():
    doc=frappe.get_single("Print Settings"); sync_print_settings(doc)
    from qfap_adds.printing.provisioning import apply_print_format_settings
    result=apply_print_format_settings()
    legacy=frappe.get_single("QFAP Print Format Settings") if frappe.db.exists("DocType","QFAP Print Format Settings") else None
    if legacy:
        frappe.db.set_single_value("Print Settings","qorg_last_sync_on",legacy.get("last_sync_on")); frappe.db.set_single_value("Print Settings","qorg_last_sync_summary",legacy.get("last_sync_summary")); frappe.db.set_single_value("Print Settings","qorg_managed_once",legacy.get("managed_once"))
    return result
