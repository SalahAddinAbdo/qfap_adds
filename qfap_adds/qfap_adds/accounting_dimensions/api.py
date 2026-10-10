from __future__ import annotations

import frappe


@frappe.whitelist()
def get_dimension_context(doctype):
    dimensions = []
    if frappe.db.exists("DocType", "Accounting Dimension"):
        dimensions = frappe.get_all("Accounting Dimension", filters={"disabled": 0}, fields=["label", "fieldname", "document_type"], limit_page_length=0)
    meta = frappe.get_meta(doctype)
    tables = [{"fieldname": df.fieldname, "options": df.options} for df in meta.fields if df.fieldtype == "Table" and df.options]
    return {"dimensions": dimensions, "tables": tables}


@frappe.whitelist()
def get_budget_lines(projects=None, txt=""):
    projects = frappe.parse_json(projects) if isinstance(projects, str) else projects
    projects = projects or []
    if not projects:
        return []
    filters={"project":["in",projects], "status":["!=","Inactive"]}
    rows=frappe.get_list("Budget Line", filters=filters, or_filters={"budget_line":["like",f"%{txt}%"],"name1":["like",f"%{txt}%"]} if txt else {},
        fields=["name","budget_line","name1","project","is_group"], order_by="project asc, lft asc", limit_page_length=100)
    return [{"value":r.name,"label":" - ".join(x for x in [r.budget_line,r.name1] if x),"description":f"Project: {r.project}"} for r in rows]
