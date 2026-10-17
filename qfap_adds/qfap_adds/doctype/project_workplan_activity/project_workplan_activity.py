from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, flt

from qfap_adds.qfap_adds.project_management.services.workplan_sync import sync_activity_task, validate_activity_deletion


class ProjectWorkplanActivity(Document):
    def autoname(self):
        self._set_sequence_and_code()
        self.activity_code = str(self.activity_code or "").strip()
        if not self.activity_code:
            frappe.throw(_("Activity Code could not be generated."))
        self.name = f"{self.project}-{self.activity_code}"
        if frappe.db.exists(self.doctype, self.name):
            frappe.throw(_("Activity ID {0} already exists.").format(frappe.bold(self.name)))

    def validate(self):
        self.activity_code = str(self.activity_code or "").strip()
        if not self.activity_code:
            frappe.throw(_("Activity Code is required."))
        self._validate_dates()
        self._validate_links()
        self._validate_measurement()
        self._set_responsibility()
        self._validate_unique_code()
        self._set_lock_and_health()

    def on_update(self):
        sync_activity_task(self)

    def on_trash(self):
        validate_activity_deletion(self)

    def _set_sequence_and_code(self):
        if not self.project or not self.project_output:
            frappe.throw(_("Project and Project Output are required."))
        used={int(value or 0) for value in frappe.get_all(self.doctype, filters={"project":self.project,"project_output":self.project_output}, pluck="sequence")}
        sequence=1
        while sequence in used: sequence += 1
        self.sequence=sequence
        if self.use_custom_code:
            self.activity_code=str(self.activity_code or "").strip()
            if not self.activity_code: frappe.throw(_("Activity Code is required when Use Custom Code is enabled."))
        else:
            output_code=frappe.db.get_value("Project Result", self.project_output, "result_code") or ""
            self.activity_code=f"{output_code}.{sequence}"

    def _validate_unique_code(self):
        filters = {
            "project": self.project,
            "activity_code": self.activity_code,
            "name": ["!=", self.name or ""],
        }
        if frappe.db.exists(self.doctype, filters):
            frappe.throw(_("Activity Code already exists in this Project."))

    def _validate_dates(self):
        if self.planned_start_date and self.planned_end_date:
            if self.planned_end_date < self.planned_start_date: frappe.throw(_("Planned End Date cannot be before Planned Start Date."))
            self.planned_duration_days=date_diff(self.planned_end_date,self.planned_start_date)+1
        if self.actual_start_date and self.actual_end_date and self.actual_end_date < self.actual_start_date:
            frappe.throw(_("Actual End Date cannot be before Actual Start Date."))

    def _validate_links(self):
        output=frappe.db.get_value("Project Result", self.project_output, ["project","result_level","sector","status"], as_dict=True)
        if not output or output.project != self.project or output.result_level != "Output":
            frappe.throw(_("Project Output must be an Output result from the selected Project."))
        if output.status == "Inactive": frappe.throw(_("Inactive Project Outputs cannot be used."))
        self.sector=output.sector
        if self.predecessor_activity:
            predecessor=frappe.db.get_value(self.doctype,self.predecessor_activity,"project")
            if predecessor != self.project: frappe.throw(_("Predecessor Activity must belong to the same Project."))
        if self.primary_budget_line:
            budget_project=frappe.db.get_value("Budget Line",self.primary_budget_line,"project")
            if budget_project != self.project: frappe.throw(_("Primary Budget Line must belong to the selected Project."))
        if self.implementation_mode == "Direct Implementation": self.implementation_partner=None

    def _validate_measurement(self):
        if flt(self.weight) < 0 or flt(self.weight) > 100: frappe.throw(_("Weight must be between 0 and 100."))
        if self.progress_measurement_method == "Percentage":
            self.unit_of_measure="Percent"; self.planned_quantity=100
        elif self.progress_measurement_method == "Milestone":
            self.unit_of_measure="Milestone"; self.planned_quantity=1
        if flt(self.approved_progress) < 0 or flt(self.approved_progress) > 100:
            frappe.throw(_("Approved Progress must be between 0 and 100."))

    def _set_responsibility(self):
        employee=frappe.db.get_value("Employee",self.responsible_employee,["status","department"],as_dict=True)
        if not employee or employee.status != "Active": frappe.throw(_("Responsible Employee must be active."))
        manager=frappe.db.get_value("Project",self.project,"custom_project_manager") or ""
        active_team=frappe.db.exists("Project Core Team Assignment", {"parent":self.project,"parenttype":"Project","employee":self.responsible_employee,"active":1})
        if self.responsible_employee != manager and not active_team:
            frappe.throw(_("Responsible Employee must be the Project Manager or an active Project Core Team member."))
        self.responsible_department=employee.department or ""

    def _set_lock_and_health(self):
        self.activity_locked=1 if self.status in ("Approved","Completed","Inactive","Cancelled") else 0
        if self.status == "Completed": self.activity_health="Completed"
        elif self.status == "On Hold": self.activity_health="On Hold"
