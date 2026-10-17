from __future__ import annotations
import frappe
from qfap_adds.qfap_adds.project_management.settings import get_project_cycle_settings
STATES=("Draft","Under Review","Approved","Rejected","Implemented","Closed")
WORKFLOWS={
 "Project Progress Update":("Draft","Submitted","Under Review","Approved","Rejected","Cancelled"),
 "Project Change Request":("Draft","Under Review","Approved","Rejected","Implemented","Closed"),
 "Project Compliance Deliverable":("Draft","Submitted","Under Review","Approved","Rejected","Cancelled"),
 "Project Beneficiary Plan":("Draft","Under Review","Approved","Rejected","Closed"),
 "Project Closure":("Draft","Under Review","Approved","Rejected","Closed"),
}
def _state(name):
    if frappe.db.exists("Workflow State",name): return
    frappe.get_doc({"doctype":"Workflow State","workflow_state_name":name,"style":"Success" if name in ("Approved","Closed","Implemented") else "Primary"}).insert(ignore_permissions=True)
def provision_project_workflows():
    settings=get_project_cycle_settings()
    mappings={row.process_doctype: row for row in settings.project_workflow_role_mappings if row.get("enabled")}
    for values in WORKFLOWS.values():
        for state in values: _state(state)
    for doctype,states in WORKFLOWS.items():
        name=f"QFAP {doctype} Workflow"
        if frappe.db.exists("Workflow",name): continue
        meta=frappe.get_meta(doctype)
        if not meta.has_field("workflow_state"): continue
        mapping=mappings.get(doctype)
        owner=(mapping.draft_owner_role if mapping else "System Manager")
        reviewer=(mapping.reviewer_role if mapping else "System Manager")
        approver=(mapping.approver_role if mapping else "System Manager")
        workflow=frappe.new_doc("Workflow"); workflow.workflow_name=name; workflow.document_type=doctype; workflow.workflow_state_field="workflow_state"; workflow.is_active=0
        for idx,state in enumerate(states): workflow.append("states",{"state":state,"doc_status":0,"allow_edit": owner if idx==0 else (reviewer if state in ("Submitted","Under Review") else approver)})
        for current,next_state,action in ((states[0],states[1],"Submit for Review"),(states[1],"Approved","Approve"),(states[1],"Rejected","Reject")):
            if current in states and next_state in states: workflow.append("transitions",{"state":current,"action":action,"next_state":next_state,"allowed": owner if action=="Submit for Review" else approver})
        workflow.insert(ignore_permissions=True)
