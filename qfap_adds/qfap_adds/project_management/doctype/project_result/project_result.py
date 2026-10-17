from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class ProjectResult(Document):
    def autoname(self):
        self._set_sequence_and_code()
        self.name = f"{self.project}-{self.result_code}"

    def validate(self):
        self._validate_structure()
        self._validate_responsibility()
        self._validate_unique_code()
        self.result_locked = 1 if self.status == "Approved" else 0

    def _set_sequence_and_code(self):
        if not self.project or not self.result_level:
            frappe.throw(_("Project and Result Level are required."))
        filters = {"project": self.project, "result_level": self.result_level}
        if self.result_level == "Output":
            if not self.parent_result:
                frappe.throw(_("Parent Result is required for Output results."))
            filters["parent_result"] = self.parent_result
        used = {int(value or 0) for value in frappe.get_all(self.doctype, filters=filters, pluck="sequence")}
        sequence = 1
        while sequence in used: sequence += 1
        self.sequence = sequence
        if self.use_custom_code:
            self.result_code = str(self.result_code or "").strip()
            if not self.result_code: frappe.throw(_("Result Code is required when Use Custom Code is enabled."))
        elif self.result_level == "Impact / Goal": self.result_code = f"G{sequence}"
        elif self.result_level == "Outcome": self.result_code = f"OC{sequence}"
        else:
            parent_code = frappe.db.get_value(self.doctype, self.parent_result, "result_code") or ""
            parent_number = parent_code[2:] if parent_code.startswith("OC") else parent_code
            self.result_code = f"OP{parent_number}.{sequence}"

    def _validate_structure(self):
        if flt(self.weight) < 0 or flt(self.weight) > 100:
            frappe.throw(_("Weight must be between 0 and 100."))
        required = {"Outcome": "Impact / Goal", "Output": "Outcome"}.get(self.result_level)
        if not required:
            self.parent_result = None
            return
        if not self.parent_result: frappe.throw(_("Parent Result is required."))
        parent = frappe.db.get_value(self.doctype, self.parent_result, ["project","result_level","sector","status"], as_dict=True)
        if not parent or parent.project != self.project: frappe.throw(_("Parent Result must belong to the selected Project."))
        if parent.result_level != required: frappe.throw(_("Parent Result level is not valid."))
        if parent.status == "Inactive": frappe.throw(_("Inactive Results cannot be selected as parents."))
        if parent.sector != self.sector: frappe.throw(_("Result Sector must match the Parent Result Sector."))

    def _validate_responsibility(self):
        employee = frappe.db.get_value("Employee", self.responsible_employee, ["status","department"], as_dict=True)
        if not employee or employee.status != "Active": frappe.throw(_("Responsible Employee must be active."))
        manager = frappe.db.get_value("Project", self.project, "custom_project_manager") or ""
        active_team = frappe.db.exists("Project Core Team Assignment", {"parent":self.project,"parenttype":"Project","employee":self.responsible_employee,"active":1})
        if self.responsible_employee != manager and not active_team:
            frappe.throw(_("Responsible Employee must be the Project Manager or an active Project Core Team member."))
        self.responsible_department = employee.department or ""

    def _validate_unique_code(self):
        filters={"project":self.project,"result_code":self.result_code,"name":["!=",self.name or ""]}
        if frappe.db.exists(self.doctype, filters): frappe.throw(_("Result Code already exists in this Project."))
