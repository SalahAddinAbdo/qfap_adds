from __future__ import annotations
import hashlib, frappe

OPEN_STATES=["Draft","Pending Approval","Approved","Application Failed"]
def request_key(doc):
    raw="|".join([doc.request_type or "",doc.requested_assignee or "",doc.project or "",doc.subject or "",str(doc.exp_start_date or ""),str(doc.exp_end_date or ""),doc.parent_task or ""])
    return hashlib.sha256(raw.encode()).hexdigest()
def validate_request_duplicate(doc):
    doc.duplicate_key=request_key(doc)
    filters={"duplicate_key":doc.duplicate_key,"workflow_state":["in",OPEN_STATES],"name":["!=",doc.name or ""]}
    other=frappe.db.get_value("Task Assignment Request",filters,"name")
    if other:frappe.throw("A matching open Task Assignment Request already exists: "+other)
def validate_task_tree(task_name,parent_name):
    if not parent_name:return
    if task_name and task_name==parent_name:frappe.throw("A task cannot be its own parent.")
    seen=set(); cursor=parent_name
    while cursor:
        if cursor in seen:frappe.throw("A circular Task hierarchy already exists.")
        seen.add(cursor)
        if task_name and cursor==task_name:frappe.throw("The selected main task would create a circular hierarchy.")
        cursor=frappe.db.get_value("Task",cursor,"parent_task") or ""
