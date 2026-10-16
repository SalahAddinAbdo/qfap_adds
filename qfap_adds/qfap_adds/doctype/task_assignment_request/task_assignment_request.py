from __future__ import annotations
import hashlib, frappe
from frappe.model.document import Document
from frappe.utils import now
from qfap_adds.qfap_adds.task_management.assignment_scope import employee_for_user, can_manage_employee
from qfap_adds.qfap_adds.task_management.duplicate_guard import validate_request_duplicate, validate_task_tree
from qfap_adds.qfap_adds.task_management.project_period import validate_period

class TaskAssignmentRequest(Document):
    def before_insert(self):
        self.requested_by_user=frappe.session.user; self.requested_by_employee=employee_for_user(); self.requested_on=now(); self.application_status="Not Applied"
    def validate(self):
        validate_request_duplicate(self); validate_task_tree(None,self.parent_task)
        validate_period(self.project,self.exp_start_date,self.exp_end_date,False,True)
        old=self.get_doc_before_save()
        old_state=old.workflow_state if old else None
        if self.workflow_state in ("Approved", "Rejected") and old_state != self.workflow_state:
            if frappe.session.user==self.requested_by_user and frappe.get_single("Task Management Settings").prevent_self_approval:
                frappe.throw("The requester cannot decide their own assignment request.")
            if not can_manage_employee(self.requested_assignee):
                frappe.throw("Only an authorized supervisor or Task Management Administrator can approve or reject this request.")
    def on_update(self):
        old=self.get_doc_before_save(); old_state=old.workflow_state if old else None
        if self.workflow_state in ("Approved","Rejected") and old_state!=self.workflow_state:
            self.db_set("decision_by",frappe.session.user,update_modified=False); self.db_set("decision_on",now(),update_modified=False)
        if self.workflow_state=="Approved" and old_state!="Approved":
            self.apply_approved_request()
    def apply_approved_request(self):
        if self.created_task:
            return
        if not can_manage_employee(self.requested_assignee):
            frappe.throw("You are not authorized to approve a task for this employee.")
        fingerprint=hashlib.sha256((self.name+"|"+self.requested_assignee+"|"+self.subject).encode()).hexdigest()
        if frappe.db.exists("Task Assignment Request",{"application_fingerprint":fingerprint,"created_task":["is","set"],"name":["!=",self.name]}):
            frappe.throw("This approved request has already been applied.")
        try:
            task=frappe.get_doc({"doctype":"Task","subject":self.subject,"description":self.description,"project":self.project,"parent_task":self.parent_task,"priority":self.priority,"exp_start_date":self.exp_start_date,"exp_end_date":self.exp_end_date,"expected_time":self.expected_time,"custom_assign_to":self.requested_assignee,"custom_self_assigned":0,"custom_task_assigned_by":employee_for_user(frappe.session.user),"custom_project_workplan":0})
            task.flags.from_assignment_request=True; task.insert(ignore_permissions=True)
            self.db_set("created_task", task.name, update_modified=False)
            self.db_set("application_fingerprint", fingerprint, update_modified=False)
            self.db_set("application_status", "Applied", update_modified=False)
            self.db_set("application_error", "", update_modified=False)
            self.db_set("workflow_state", "Applied", update_modified=False)
            self.add_comment("Info","Task "+task.name+" was created automatically after supervisor approval and assigned to "+self.requested_assignee+".")
        except Exception:
            error = frappe.get_traceback()
            self.db_set("application_status", "Failed", update_modified=False)
            self.db_set("application_error", error, update_modified=False)
            self.db_set("workflow_state", "Application Failed", update_modified=False)
            frappe.log_error(error, "Task Assignment Request application failed: " + self.name)
            raise
