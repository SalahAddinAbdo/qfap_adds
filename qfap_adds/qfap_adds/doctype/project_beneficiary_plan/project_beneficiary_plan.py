from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from qfap_adds.qfap_adds.project_management.services.common import unique_child_rows
class ProjectBeneficiaryPlan(Document):
    def validate(self):
        unique_child_rows(self,"beneficiary_breakdown",("governorate","district","beneficiary_type","gender","age_group","disability_status"),"Beneficiary Breakdown")
        rows=self.get("beneficiary_breakdown") or []
        self.planned_individuals_total=sum(flt(r.get("planned_individuals")) for r in rows)
        self.actual_individuals_total=sum(flt(r.get("actual_individuals")) for r in rows)
        self.planned_households_total=sum(flt(r.get("planned_households")) for r in rows)
        self.actual_households_total=sum(flt(r.get("actual_households")) for r in rows)
        self.planned_pwd_total=sum(flt(r.get("planned_pwd")) for r in rows)
        self.actual_pwd_total=sum(flt(r.get("actual_pwd")) for r in rows)
        self.individual_achievement_total=(self.actual_individuals_total/self.planned_individuals_total*100) if self.planned_individuals_total else 0
        self.household_achievement_total=(self.actual_households_total/self.planned_households_total*100) if self.planned_households_total else 0
        if self.actuals_finalized:
            self.actuals_finalized_on=self.actuals_finalized_on or nowdate(); self.actuals_finalized_by=self.actuals_finalized_by or frappe.session.user
    def on_update(self):
        meta=frappe.get_meta("Project"); updates={}
        for field,value in (("custom_planned_beneficiaries",self.planned_individuals_total),("custom_actual_beneficiaries",self.actual_individuals_total)):
            if meta.has_field(field): updates[field]=value
        if updates: frappe.db.set_value("Project",self.project,updates,update_modified=False)
