from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, getdate, nowdate
from qfap_adds.qfap_adds.project_management.settings import get_project_cycle_settings
from qfap_adds.qfap_adds.project_management.services.common import validate_dates, validate_team_employee, unique_child_rows
from qfap_adds.qfap_adds.project_management.services.project_reconciliation import reconcile_document_projects, reconcile_deleted_document, reconcile_project
class ProjectComplianceDeliverable(Document):
    def validate(self):
        validate_dates(self.period_start_date,self.period_end_date,"Period Start Date","Period End Date")
        self.responsible_department=validate_team_employee(self.project,self.responsible_employee,"Responsible Employee")
        if self.review_responsible: self.review_department=validate_team_employee(self.project,self.review_responsible,"Review Responsible")
        unique_child_rows(self,"attachment_requirements",("attachment_type","description"),"Attachment Requirement")
        settings=get_project_cycle_settings()
        if self.status in ("Submitted","Approved") and not self.submission_date: frappe.throw(_("Submission Date is required for submitted Deliverables."))
        if (self.status=="Submitted" and settings.require_mandatory_attachments_before_submission) or (self.status=="Approved" and settings.require_mandatory_attachments_before_approval):
            missing=[row.description or row.idx for row in self.get("attachment_requirements") or [] if row.get("mandatory") and not row.get("attachment")]
            if missing: frappe.throw(_("Mandatory attachment requirements are incomplete."))
        self._monitor()
    def _monitor(self):
        if self.status in ("Approved","Cancelled"):
            self.monitoring_status="Completed"; self.monitoring_days=0; return
        if not self.due_date: return
        days=date_diff(self.due_date,nowdate()); self.monitoring_days=days
        settings=get_project_cycle_settings()
        self.monitoring_status="Overdue" if days<0 else ("Due Soon" if days<=int(settings.deliverable_due_soon_days or 7) else "Not Due")
        self.monitoring_message=f"Due in {days} day(s)" if days>=0 else f"Overdue by {abs(days)} day(s)"


def _qorg_reconcile_on_update(self):
    reconcile_document_projects(self)

def _qorg_reconcile_after_delete(self):
    reconcile_deleted_document(self)

def _qorg_reconcile_on_cancel(self):
    reconcile_document_projects(self)

def _qorg_reconcile_on_update_after_submit(self):
    reconcile_document_projects(self)

_qorg_original_on_update = getattr(ProjectComplianceDeliverable, "on_update", None)
def _qorg_wrapped_on_update(self):
    if _qorg_original_on_update:
        _qorg_original_on_update(self)
    reconcile_document_projects(self)
ProjectComplianceDeliverable.on_update = _qorg_wrapped_on_update

_qorg_original_after_delete = getattr(ProjectComplianceDeliverable, "after_delete", None)
def _qorg_wrapped_after_delete(self):
    if _qorg_original_after_delete:
        _qorg_original_after_delete(self)
    reconcile_deleted_document(self)
ProjectComplianceDeliverable.after_delete = _qorg_wrapped_after_delete

_qorg_original_on_cancel = getattr(ProjectComplianceDeliverable, "on_cancel", None)
def _qorg_wrapped_on_cancel(self):
    if _qorg_original_on_cancel:
        _qorg_original_on_cancel(self)
    reconcile_document_projects(self)
ProjectComplianceDeliverable.on_cancel = _qorg_wrapped_on_cancel

_qorg_original_on_update_after_submit = getattr(ProjectComplianceDeliverable, "on_update_after_submit", None)
def _qorg_wrapped_on_update_after_submit(self):
    if _qorg_original_on_update_after_submit:
        _qorg_original_on_update_after_submit(self)
    reconcile_document_projects(self)
ProjectComplianceDeliverable.on_update_after_submit = _qorg_wrapped_on_update_after_submit
