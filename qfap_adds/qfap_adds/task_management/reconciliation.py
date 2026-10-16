from __future__ import annotations

import importlib
import json, frappe
from frappe.utils import now
from qfap_adds.qfap_adds.task_management.services import rebuild_chain
from qfap_adds.qfap_adds.task_management.services import sync

def reconcile_all(dry_run=True,task=None,project=None,company=None,batch_size=200):
    filters={}
    if task:filters["name"]=task
    if project:filters["project"]=project
    rows=frappe.get_all("Task",filters=filters,pluck="name",limit_page_length=int(batch_size or 200)); out={"scanned":0,"changed":0,"warnings":0,"errors":0,"rollups_rebuilt":0,"shares_reconciled":0,"dry_run":bool(dry_run)}
    for name in rows:
        out["scanned"]+=1
        try:
            doc=frappe.get_doc("Task",name)
            if not dry_run:
                sync(doc); rebuild_chain(doc.parent_task); out["shares_reconciled"]+=1; out["rollups_rebuilt"]+=1
        except Exception:
            out["errors"]+=1; frappe.log_error(frappe.get_traceback(),"Task reconciliation: "+name)
    if not dry_run and frappe.db.exists("DocType","Task Management Settings"):
        frappe.db.set_single_value("Task Management Settings","last_reconciliation_on",now()); frappe.db.set_single_value("Task Management Settings","last_reconciliation_status","Completed with errors" if out["errors"] else "Completed"); frappe.db.set_single_value("Task Management Settings","last_reconciliation_summary",json.dumps(out))
    return out


# Installation and integration diagnostics
def task_integration_health():
    required_doctypes = [
        "Task Management Settings", "Task Assignment Request", "QFAP Managed Task Share",
        "Task Management Role Row", "Task Summary Recipient",
    ]
    doctypes = {name: bool(frappe.db.exists("DocType", name)) for name in required_doctypes}
    settings_single = doctypes["Task Management Settings"] and bool(frappe.get_meta("Task Management Settings").issingle)
    workflow_actions = {name: bool(frappe.db.exists("Workflow Action Master", {"workflow_action_name": name})) for name in ("Submit for Approval", "Approve", "Reject")}
    legacy_server = frappe.get_all("Server Script", filters={"disabled": 0, "name": ["like", "%Task%"]}, pluck="name") if frappe.db.exists("DocType", "Server Script") else []
    legacy_client = frappe.get_all("Client Script", filters={"enabled": 1, "dt": "Task"}, pluck="name") if frappe.db.exists("DocType", "Client Script") else []
    report_import = True
    try:
        importlib.import_module("qfap_adds.qfap_adds.report.employees_task_tracker.employees_task_tracker")
    except Exception:
        report_import = False
    result = {
        "ok": all(doctypes.values()) and settings_single and all(workflow_actions.values()) and report_import,
        "doctypes": doctypes,
        "settings_is_single": settings_single,
        "workflow_actions": workflow_actions,
        "workflow": bool(frappe.db.exists("Workflow", "Task Assignment Request Approval")),
        "roles": {role: bool(frappe.db.exists("Role", role)) for role in ("Task Management Administrator", "Reports Viewer")},
        "report": bool(frappe.db.exists("Report", "Employees Task Tracker")),
        "report_import": report_import,
        "enabled_legacy_server_scripts": legacy_server,
        "enabled_task_client_scripts": legacy_client,
    }
    return result

