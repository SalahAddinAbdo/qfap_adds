from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document
class ProjectProgressUpdate(Document):
    def validate(self):
        if self.period_start_date and self.period_end_date and self.period_end_date < self.period_start_date: frappe.throw(_("Period End Date cannot be before Period Start Date."))
        duplicate={"project":self.project,"period_start_date":self.period_start_date,"period_end_date":self.period_end_date,"name":["!=",self.name or ""]}
        if frappe.db.exists(self.doctype,duplicate): frappe.throw(_("A Progress Update already exists for this Project and reporting period."))
        self.update_locked=1 if self.status in ("Approved","Submitted") else 0
    def on_update(self):
        if self.status=="Approved": self._apply_approved_entries()
    def _apply_approved_entries(self):
        for row in self.get("activity_progress_entries") or []:
            frappe.db.set_value("Project Workplan Activity",row.activity,{"actual_quantity":row.cumulative_actual_quantity,"approved_progress":row.progress_percentage,"status":row.period_status},update_modified=False)
