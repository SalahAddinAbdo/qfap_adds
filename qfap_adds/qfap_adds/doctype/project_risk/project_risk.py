from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, add_days, flt, nowdate
from qfap_adds.qfap_adds.project_management.settings import get_project_cycle_settings
from qfap_adds.qfap_adds.project_management.services.common import numeric_rating, validate_project_link, validate_team_employee
from qfap_adds.qfap_adds.project_management.services.project_summary import rebuild_project_summary
from qfap_adds.qfap_adds.project_management.services.project_reconciliation import reconcile_document_projects, reconcile_deleted_document, reconcile_project
class ProjectRisk(Document):
    def before_insert(self):
        self.assessment_date=self.assessment_date or nowdate()
    def validate(self):
        self.risk_score=numeric_rating(self.probability)*numeric_rating(self.impact)
        settings=get_project_cycle_settings()
        self.risk_level=self._level(self.risk_score, settings)
        self.residual_risk_score=numeric_rating(self.residual_probability)*numeric_rating(self.residual_impact)
        self.residual_risk_level=self._level(self.residual_risk_score, settings)
        self.responsible_department=validate_team_employee(self.project,self.risk_owner,"Risk Owner")
        for field,dt,label in (("related_output","Project Result","Related Output"),("related_activity","Project Workplan Activity","Related Activity"),("related_indicator","Project Indicator","Related Indicator")):
            validate_project_link(self.project,dt,self.get(field),label)
        if flt(self.mitigation_progress)<0 or flt(self.mitigation_progress)>100: frappe.throw(_("Mitigation Progress must be between 0 and 100."))
        if settings.critical_risk_escalation_enabled:
            self.escalation_required=1 if self.risk_level in ("High","Critical") else self.escalation_required
        self.risk_locked=1 if self.status in ("Closed","Inactive") else 0
    def on_update(self):
        settings=get_project_cycle_settings()
        if settings.auto_create_issue_when_risk_occurs and self.occurred and not self.related_issue: self._create_issue()
        rebuild_project_summary(self.project)
    def on_trash(self):
        if self.related_issue: frappe.throw(_("A Risk linked to an Issue cannot be deleted."))
    def _create_issue(self):
        issue=frappe.new_doc("Issue"); issue.subject=f"Risk Occurred: {self.risk_title}"; issue.description=self.occurrence_notes or self.risk_description
        if issue.meta.has_field("project"): issue.project=self.project
        if issue.meta.has_field("custom_project_risk"): issue.custom_project_risk=self.name
        issue.insert(ignore_permissions=True); frappe.db.set_value(self.doctype,self.name,"related_issue",issue.name,update_modified=False); self.related_issue=issue.name
    @staticmethod
    def _level(score, settings):
        if not score:return "Not Assessed"
        if score<=settings.low_risk_maximum_score:return "Low"
        if score<=settings.moderate_risk_maximum_score:return "Moderate"
        if score<=settings.high_risk_maximum_score:return "High"
        return "Critical"


def _qorg_reconcile_on_update(self):
    reconcile_document_projects(self)

def _qorg_reconcile_after_delete(self):
    reconcile_deleted_document(self)

def _qorg_reconcile_on_cancel(self):
    reconcile_document_projects(self)

def _qorg_reconcile_on_update_after_submit(self):
    reconcile_document_projects(self)

_qorg_original_on_update = getattr(ProjectRisk, "on_update", None)
def _qorg_wrapped_on_update(self):
    if _qorg_original_on_update:
        _qorg_original_on_update(self)
    reconcile_document_projects(self)
ProjectRisk.on_update = _qorg_wrapped_on_update

_qorg_original_after_delete = getattr(ProjectRisk, "after_delete", None)
def _qorg_wrapped_after_delete(self):
    if _qorg_original_after_delete:
        _qorg_original_after_delete(self)
    reconcile_deleted_document(self)
ProjectRisk.after_delete = _qorg_wrapped_after_delete

_qorg_original_on_cancel = getattr(ProjectRisk, "on_cancel", None)
def _qorg_wrapped_on_cancel(self):
    if _qorg_original_on_cancel:
        _qorg_original_on_cancel(self)
    reconcile_document_projects(self)
ProjectRisk.on_cancel = _qorg_wrapped_on_cancel

_qorg_original_on_update_after_submit = getattr(ProjectRisk, "on_update_after_submit", None)
def _qorg_wrapped_on_update_after_submit(self):
    if _qorg_original_on_update_after_submit:
        _qorg_original_on_update_after_submit(self)
    reconcile_document_projects(self)
ProjectRisk.on_update_after_submit = _qorg_wrapped_on_update_after_submit
