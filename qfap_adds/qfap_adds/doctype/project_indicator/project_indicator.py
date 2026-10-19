from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from qfap_adds.qfap_adds.project_management.api import validate_project_team_employee

from qfap_adds.qfap_adds.project_management.services.project_reconciliation import reconcile_document_projects, reconcile_deleted_document, reconcile_project
class ProjectIndicator(Document):
    def autoname(self):
        self._set_code()
        self.name = f"{self.project}-{self.indicator_code}"
        if frappe.db.exists(self.doctype,self.name): frappe.throw(_("Indicator ID already exists."))
    def validate(self):
        self.indicator_code=str(self.indicator_code or "").strip()
        if not self.indicator_code: frappe.throw(_("Indicator Code is required."))
        result=frappe.db.get_value("Project Result",self.project_result,["project","result_level","sector","status"],as_dict=True)
        if not result or result.project != self.project: frappe.throw(_("Project Result must belong to the selected Project."))
        if result.status == "Inactive": frappe.throw(_("Inactive Results cannot be used."))
        self.sector=result.sector; self.indicator_level="Impact" if result.result_level=="Impact / Goal" else result.result_level
        self.responsible_department=validate_project_team_employee(self.project,self.data_collection_responsible_employee,"Data Collection Responsible Employee")
        if flt(self.life_of_project_target) < 0: frappe.throw(_("Life of Project Target cannot be negative."))
        if frappe.db.exists(self.doctype,{"project":self.project,"indicator_code":self.indicator_code,"name":["!=",self.name or ""]}): frappe.throw(_("Indicator Code already exists in this Project."))
        self.indicator_locked=1 if self.status=="Approved" else 0
    def _set_code(self):
        if not self.project or not self.project_result: frappe.throw(_("Project and Project Result are required."))
        if self.use_custom_code:
            self.indicator_code=str(self.indicator_code or "").strip()
            if not self.indicator_code: frappe.throw(_("Indicator Code is required when Use Custom Code is enabled."))
            return
        result_code=frappe.db.get_value("Project Result",self.project_result,"result_code") or ""
        used={int(v or 0) for v in frappe.get_all(self.doctype,filters={"project":self.project,"project_result":self.project_result},pluck="sequence")}
        sequence=1
        while sequence in used: sequence+=1
        self.sequence=sequence; self.indicator_code=f"{result_code}.I{sequence}"


def _qorg_reconcile_on_update(self):
    reconcile_document_projects(self)

def _qorg_reconcile_after_delete(self):
    reconcile_deleted_document(self)

def _qorg_reconcile_on_cancel(self):
    reconcile_document_projects(self)

def _qorg_reconcile_on_update_after_submit(self):
    reconcile_document_projects(self)

_qorg_original_on_update = getattr(ProjectIndicator, "on_update", None)
def _qorg_wrapped_on_update(self):
    if _qorg_original_on_update:
        _qorg_original_on_update(self)
    reconcile_document_projects(self)
ProjectIndicator.on_update = _qorg_wrapped_on_update

_qorg_original_after_delete = getattr(ProjectIndicator, "after_delete", None)
def _qorg_wrapped_after_delete(self):
    if _qorg_original_after_delete:
        _qorg_original_after_delete(self)
    reconcile_deleted_document(self)
ProjectIndicator.after_delete = _qorg_wrapped_after_delete

_qorg_original_on_cancel = getattr(ProjectIndicator, "on_cancel", None)
def _qorg_wrapped_on_cancel(self):
    if _qorg_original_on_cancel:
        _qorg_original_on_cancel(self)
    reconcile_document_projects(self)
ProjectIndicator.on_cancel = _qorg_wrapped_on_cancel

_qorg_original_on_update_after_submit = getattr(ProjectIndicator, "on_update_after_submit", None)
def _qorg_wrapped_on_update_after_submit(self):
    if _qorg_original_on_update_after_submit:
        _qorg_original_on_update_after_submit(self)
    reconcile_document_projects(self)
ProjectIndicator.on_update_after_submit = _qorg_wrapped_on_update_after_submit
