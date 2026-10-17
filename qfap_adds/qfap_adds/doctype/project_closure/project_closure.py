from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from qfap_adds.qfap_adds.project_management.settings import get_project_cycle_settings
from qfap_adds.qfap_adds.project_management.services.readiness import assess as assess_closure
from qfap_adds.qfap_adds.project_management.services.common import average_ratings, validate_dates, validate_team_employee, unique_child_rows
class ProjectClosure(Document):
    def validate(self):
        validate_dates(self.planned_closure_date,self.actual_closure_date,"Planned Closure Date","Actual Closure Date")
        self.coordinator_department=validate_team_employee(self.project,self.closure_coordinator,"Closure Coordinator")
        unique_child_rows(self,"checklist_items",("item","description"),"Checklist Item")
        unique_child_rows(self,"outstanding_actions",("action","responsible_employee","due_date"),"Outstanding Action")
        for row in self.get("outstanding_actions") or []:
            if row.responsible_employee: validate_team_employee(self.project,row.responsible_employee,"Outstanding Action Responsible Employee")
        self.overall_evaluation_score=average_ratings(self,("relevance_rating","effectiveness_rating","efficiency_rating","impact_rating","sustainability_rating","compliance_rating"))
        self._readiness()
    def before_submit(self):
        self._readiness()
        if self.overall_closure_status not in ("Ready for Closure","Ready","Completed"): frappe.throw(_("Project Closure is not ready for submission."))
        if not self.lessons_learned or not self.sustainability_plan: frappe.throw(_("Lessons Learned and Sustainability Plan are required."))
    def on_submit(self):
        self.project_closed=1; self.actual_closure_date=self.actual_closure_date or nowdate()
        frappe.db.set_value("Project",self.project,{"status":"Completed","percent_complete":100},update_modified=False)
    def _readiness(self):
        assessment = assess_closure(self.project)
        checklist=self.get("checklist_items") or []; incomplete=[r for r in checklist if not r.get("completed")]
        open_actions=[r for r in self.get("outstanding_actions") or [] if r.get("status") not in ("Completed","Cancelled")]
        settings=get_project_cycle_settings()
        required_docs=(not settings.require_final_technical_report or bool(self.final_technical_report)) and (not settings.require_final_financial_report or bool(self.final_financial_report)) and (not settings.require_archive_reference or bool(self.archive_reference))
        self.overall_closure_status="Ready for Closure" if assessment["ready"] and not incomplete and not open_actions and required_docs else "Not Ready"
