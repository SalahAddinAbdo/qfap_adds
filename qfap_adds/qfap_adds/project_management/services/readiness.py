from __future__ import annotations
import frappe
from frappe.utils import flt
from qfap_adds.qfap_adds.project_management.settings import get_project_cycle_settings

def assess(project):
    checks=[]
    def add(key,label,passed,blocking=True,detail=""):
        checks.append({"key":key,"label":label,"passed":bool(passed),"blocking":blocking,"detail":detail})
    open_risks=frappe.db.count("Project Risk",{"project":project,"status":["not in",["Closed","Inactive"]],"risk_level":["in",["High","Critical"]]})
    open_changes=frappe.db.count("Project Change Request",{"project":project,"status":["not in",["Implemented","Closed","Rejected","Cancelled"]]})
    overdue=frappe.db.count("Project Compliance Deliverable",{"project":project,"monitoring_status":["in",["Overdue","Critical"]]})
    beneficiary=frappe.db.exists("Project Beneficiary Plan",{"project":project,"actuals_finalized":1})
    add("risks","No open High/Critical Risks",open_risks==0,True,str(open_risks))
    add("changes","No pending Change Requests",open_changes==0,True,str(open_changes))
    add("compliance","No overdue mandatory Deliverables",overdue==0,True,str(overdue))
    add("beneficiaries","Beneficiary actuals finalized",bool(beneficiary),True)
    settings=get_project_cycle_settings()
    if settings.warn_about_open_tasks_during_closure:
        open_tasks=frappe.db.count("Task",{"project":project,"status":["not in",["Completed","Cancelled"]]})
        add("tasks","No open operational Tasks",open_tasks==0,bool(settings.block_closure_when_open_tasks_exist),str(open_tasks))
    configured={row.gate_key: row for row in settings.project_readiness_gates if row.get("enabled")}
    for check in checks:
        if check["key"] in configured: check["blocking"]=bool(configured[check["key"]].blocking)
    ready=not any(not c["passed"] and c["blocking"] for c in checks)
    return {"ready":ready,"checks":checks}
