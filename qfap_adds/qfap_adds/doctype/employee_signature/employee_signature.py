from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class EmployeeSignature(Document):
    def validate(self):
        if self.is_employee == "Yes" and not self.employee_ref:
            frappe.throw(_("Employee Ref is required for employee signatures."))
        if self.employee_ref:
            employee = frappe.db.get_value("Employee", self.employee_ref,
                ["employee_name", "designation", "cell_number", "user_id"], as_dict=True)
            if employee:
                self.full_name = employee.employee_name or self.full_name
                self.designation = employee.designation or self.designation
                self.phone_number = employee.cell_number or self.phone_number
                self.user_id = employee.user_id or self.user_id
        if not self.user_id:
            frappe.throw(_("User ID is required."))
        if self.is_default:
            duplicate = frappe.db.exists(self.doctype,
                {"user_id": self.user_id, "is_default": 1, "disabled": 0, "name": ["!=", self.name or ""]})
            if duplicate:
                frappe.throw(_("Only one active default signature is allowed per user."))
