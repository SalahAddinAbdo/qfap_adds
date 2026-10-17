from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
class IndicatorTargetPlan(Document):
    def validate(self):
        indicator=frappe.db.get_value("Project Indicator",self.indicator,["project","status","life_of_project_target"],as_dict=True)
        if not indicator or indicator.project != self.project: frappe.throw(_("Indicator must belong to the selected Project."))
        if indicator.status=="Inactive": frappe.throw(_("Inactive Indicators cannot be planned."))
        if self.period_start_date and self.period_end_date and self.period_end_date < self.period_start_date: frappe.throw(_("Period End Date cannot be before Period Start Date."))
        if flt(self.target_value)<0: frappe.throw(_("Target Value cannot be negative."))
        duplicate={"project":self.project,"indicator":self.indicator,"period_start_date":self.period_start_date,"period_end_date":self.period_end_date,"name":["!=",self.name or ""]}
        if frappe.db.exists(self.doctype,duplicate): frappe.throw(_("A Target Plan already exists for this Indicator and period."))
