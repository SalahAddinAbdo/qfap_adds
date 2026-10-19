from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document
from qfap_adds.qfap_adds.project_management.services.progress_engine import validate_progress_update, apply_approved_update
from qfap_adds.qfap_adds.project_management.services.project_reconciliation import reconcile_document_projects, reconcile_deleted_document, reconcile_project
class ProjectProgressUpdate(Document):
    def validate(self):
        validate_progress_update(self)
        if self.period_start_date and self.period_end_date and self.period_end_date < self.period_start_date: frappe.throw(_("Period End Date cannot be before Period Start Date."))
        duplicate={"project":self.project,"period_start_date":self.period_start_date,"period_end_date":self.period_end_date,"name":["!=",self.name or ""]}
        if frappe.db.exists(self.doctype,duplicate): frappe.throw(_("A Progress Update already exists for this Project and reporting period."))
        self.update_locked=1 if self.status in ("Approved","Submitted") else 0
    def on_update(self):
        apply_approved_update(self)


def _qorg_reconcile_on_update(self):
    reconcile_document_projects(self)

def _qorg_reconcile_after_delete(self):
    reconcile_deleted_document(self)

def _qorg_reconcile_on_cancel(self):
    reconcile_document_projects(self)

def _qorg_reconcile_on_update_after_submit(self):
    reconcile_document_projects(self)

_qorg_original_on_update = getattr(ProjectProgressUpdate, "on_update", None)
def _qorg_wrapped_on_update(self):
    if _qorg_original_on_update:
        _qorg_original_on_update(self)
    reconcile_document_projects(self)
ProjectProgressUpdate.on_update = _qorg_wrapped_on_update

_qorg_original_after_delete = getattr(ProjectProgressUpdate, "after_delete", None)
def _qorg_wrapped_after_delete(self):
    if _qorg_original_after_delete:
        _qorg_original_after_delete(self)
    reconcile_deleted_document(self)
ProjectProgressUpdate.after_delete = _qorg_wrapped_after_delete

_qorg_original_on_cancel = getattr(ProjectProgressUpdate, "on_cancel", None)
def _qorg_wrapped_on_cancel(self):
    if _qorg_original_on_cancel:
        _qorg_original_on_cancel(self)
    reconcile_document_projects(self)
ProjectProgressUpdate.on_cancel = _qorg_wrapped_on_cancel

_qorg_original_on_update_after_submit = getattr(ProjectProgressUpdate, "on_update_after_submit", None)
def _qorg_wrapped_on_update_after_submit(self):
    if _qorg_original_on_update_after_submit:
        _qorg_original_on_update_after_submit(self)
    reconcile_document_projects(self)
ProjectProgressUpdate.on_update_after_submit = _qorg_wrapped_on_update_after_submit
