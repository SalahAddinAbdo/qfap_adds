from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document
from qfap_adds.qfap_adds.project_management.services.progress_engine import validate_progress_update, apply_approved_update
class ProjectProgressUpdate(Document):
    def validate(self):
        validate_progress_update(self)
        if self.period_start_date and self.period_end_date and self.period_end_date < self.period_start_date: frappe.throw(_("Period End Date cannot be before Period Start Date."))
        duplicate={"project":self.project,"period_start_date":self.period_start_date,"period_end_date":self.period_end_date,"name":["!=",self.name or ""]}
        if frappe.db.exists(self.doctype,duplicate): frappe.throw(_("A Progress Update already exists for this Project and reporting period."))
        self.update_locked=1 if self.status in ("Approved","Submitted") else 0
    def on_update(self):
        apply_approved_update(self)
