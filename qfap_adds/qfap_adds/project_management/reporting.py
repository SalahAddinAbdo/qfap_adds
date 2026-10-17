from __future__ import annotations
import frappe
from frappe.utils import flt

def _project_filter(filters):
    return {"name": filters.get("project")} if filters.get("project") else {}

def portfolio(filters=None):
    filters = frappe._dict(filters or {})
    columns=[{"label":"Project","fieldname":"project","fieldtype":"Link","options":"Project","width":180},{"label":"Project Name","fieldname":"project_name","width":220},{"label":"Status","fieldname":"status","width":110},{"label":"Progress %","fieldname":"progress","fieldtype":"Percent","width":100},{"label":"Health","fieldname":"health","width":110},{"label":"Critical Risks","fieldname":"critical_risks","fieldtype":"Int","width":100},{"label":"Overdue Deliverables","fieldname":"overdue_deliverables","fieldtype":"Int","width":130}]
    fields=["name","project_name","status","percent_complete"]
    meta=frappe.get_meta("Project")
    if meta.has_field("custom_calculated_project_health"): fields.append("custom_calculated_project_health")
    data=[]
    for p in frappe.get_all("Project",filters=_project_filter(filters),fields=fields,limit_page_length=0):
        data.append({"project":p.name,"project_name":p.project_name,"status":p.status,"progress":flt(p.percent_complete),"health":p.get("custom_calculated_project_health") or "Not Assessed","critical_risks":frappe.db.count("Project Risk",{"project":p.name,"risk_level":"Critical","status":["not in",["Closed","Inactive"]]}),"overdue_deliverables":frappe.db.count("Project Compliance Deliverable",{"project":p.name,"monitoring_status":["in",["Overdue","Critical"]]})})
    return columns,data

def generic(doctype, filters=None, extra_fields=None):
    filters=frappe._dict(filters or {}); db_filters={}
    if filters.get("project"): db_filters["project"]=filters.project
    if filters.get("status"): db_filters["status"]=filters.status
    fields=["name","project","status","modified"] + list(extra_fields or [])
    fields=[f for f in fields if f=="name" or frappe.get_meta(doctype).has_field(f)]
    rows=frappe.get_all(doctype,filters=db_filters,fields=fields,order_by="modified desc",limit_page_length=0)
    columns=[]
    for field in fields:
        df=frappe.get_meta(doctype).get_field(field) if field!="name" else None
        columns.append({"label": (df.label if df else doctype), "fieldname":field, "fieldtype":(df.fieldtype if df else "Link"), "options":(df.options if df else doctype), "width":180 if field in ("name","project") else 120})
    return columns,rows
