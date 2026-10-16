from __future__ import annotations
import json, frappe
from frappe.utils import now
from qfap_adds.qfap_adds.task_management.rollup import rebuild_chain
from qfap_adds.qfap_adds.task_management.sharing import sync

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
