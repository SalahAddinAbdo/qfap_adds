from __future__ import annotations
import frappe

def prepare_q_management_hub():
    for name in ("Project Cycle Management","QFap Management Hub"):
        if name != "Q Management Hub" and frappe.db.exists("Workspace",name): frappe.delete_doc("Workspace",name,ignore_permissions=True,force=True)
    frappe.clear_cache()
