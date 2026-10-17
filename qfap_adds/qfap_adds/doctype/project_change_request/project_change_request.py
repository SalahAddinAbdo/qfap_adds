from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, flt, nowdate
from qfap_adds.qfap_adds.project_management.services.change_control import apply_change_request
from qfap_adds.qfap_adds.project_management.services.common import validate_dates, validate_team_employee, unique_child_rows
class ProjectChangeRequest(Document):
    def before_insert(self):
        self.request_date=self.request_date or nowdate()
    def validate(self):
        validate_dates(self.current_project_end_date,self.proposed_project_end_date,"Current Project End Date","Proposed Project End Date")
        if self.current_project_end_date and self.proposed_project_end_date: self.schedule_change_days=date_diff(self.proposed_project_end_date,self.current_project_end_date)
        self.budget_change_amount=flt(self.proposed_project_budget)-flt(self.current_project_budget)
        self.budget_change_percentage=(self.budget_change_amount/flt(self.current_project_budget)*100) if flt(self.current_project_budget) else 0
        validate_team_employee(self.project,self.requested_by,"Requested By")
        if self.implementation_responsible: validate_team_employee(self.project,self.implementation_responsible,"Implementation Responsible")
        unique_child_rows(self,"affected_items",("reference_doctype","reference_name","field_name"),"Affected Item")
        if self.change_applied and self.status not in ("Approved","Implemented","Closed"): frappe.throw(_("Change can be marked as applied only after approval."))
        if self.actual_implementation_date and not self.change_applied: frappe.throw(_("Enable Change Applied when Actual Implementation Date is set."))
    def on_update(self):
        if self.status == "Approved" and self.change_applied:
            apply_change_request(self)
        if self.change_applied and not self.actual_implementation_date: frappe.db.set_value(self.doctype,self.name,"actual_implementation_date",nowdate(),update_modified=False)
