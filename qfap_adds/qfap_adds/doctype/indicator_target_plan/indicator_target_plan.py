from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from qfap_adds.qfap_adds.project_management.services.project_reconciliation import reconcile_document_projects, reconcile_deleted_document, reconcile_project
class IndicatorTargetPlan(Document):
    def validate(self):
        indicator=frappe.db.get_value("Project Indicator",self.indicator,["project","status","life_of_project_target"],as_dict=True)
        if not indicator or indicator.project != self.project: frappe.throw(_("Indicator must belong to the selected Project."))
        if indicator.status=="Inactive": frappe.throw(_("Inactive Indicators cannot be planned."))
        if self.period_start_date and self.period_end_date and self.period_end_date < self.period_start_date: frappe.throw(_("Period End Date cannot be before Period Start Date."))
        if flt(self.target_value)<0: frappe.throw(_("Target Value cannot be negative."))
        duplicate={"project":self.project,"indicator":self.indicator,"period_start_date":self.period_start_date,"period_end_date":self.period_end_date,"name":["!=",self.name or ""]}
        if frappe.db.exists(self.doctype,duplicate): frappe.throw(_("A Target Plan already exists for this Indicator and period."))


def _qorg_reconcile_on_update(self):
    reconcile_document_projects(self)

def _qorg_reconcile_after_delete(self):
    reconcile_deleted_document(self)

def _qorg_reconcile_on_cancel(self):
    reconcile_document_projects(self)

def _qorg_reconcile_on_update_after_submit(self):
    reconcile_document_projects(self)

_qorg_original_on_update = getattr(IndicatorTargetPlan, "on_update", None)
def _qorg_wrapped_on_update(self):
    if _qorg_original_on_update:
        _qorg_original_on_update(self)
    reconcile_document_projects(self)
IndicatorTargetPlan.on_update = _qorg_wrapped_on_update

_qorg_original_after_delete = getattr(IndicatorTargetPlan, "after_delete", None)
def _qorg_wrapped_after_delete(self):
    if _qorg_original_after_delete:
        _qorg_original_after_delete(self)
    reconcile_deleted_document(self)
IndicatorTargetPlan.after_delete = _qorg_wrapped_after_delete

_qorg_original_on_cancel = getattr(IndicatorTargetPlan, "on_cancel", None)
def _qorg_wrapped_on_cancel(self):
    if _qorg_original_on_cancel:
        _qorg_original_on_cancel(self)
    reconcile_document_projects(self)
IndicatorTargetPlan.on_cancel = _qorg_wrapped_on_cancel

_qorg_original_on_update_after_submit = getattr(IndicatorTargetPlan, "on_update_after_submit", None)
def _qorg_wrapped_on_update_after_submit(self):
    if _qorg_original_on_update_after_submit:
        _qorg_original_on_update_after_submit(self)
    reconcile_document_projects(self)
IndicatorTargetPlan.on_update_after_submit = _qorg_wrapped_on_update_after_submit
