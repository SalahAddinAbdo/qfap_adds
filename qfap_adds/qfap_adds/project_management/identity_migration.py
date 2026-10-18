from __future__ import annotations
import frappe

OLD_WORKSPACES=("QFap Management Hub","Project Cycle Management")
OLD_SIDEBARS=("QFap Adds",)
OLD_ICONS=("QFap Adds","QFap Management Hub")

def prepare_q_org_identity():
    for name in OLD_WORKSPACES:
        if name != "Q Management Hub" and frappe.db.exists("Workspace",name):
            frappe.delete_doc("Workspace",name,ignore_permissions=True,force=True)
    for name in OLD_SIDEBARS:
        if name != "Q Org" and frappe.db.exists("Workspace Sidebar",name):
            frappe.delete_doc("Workspace Sidebar",name,ignore_permissions=True,force=True)
    for name in OLD_ICONS:
        if name != "Q Org" and frappe.db.exists("Desktop Icon",name):
            frappe.delete_doc("Desktop Icon",name,ignore_permissions=True,force=True)
    frappe.clear_cache()
