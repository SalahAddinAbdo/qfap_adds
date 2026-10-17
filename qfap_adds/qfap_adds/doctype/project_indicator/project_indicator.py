from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from qfap_adds.qfap_adds.project_management.api import validate_project_team_employee

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
