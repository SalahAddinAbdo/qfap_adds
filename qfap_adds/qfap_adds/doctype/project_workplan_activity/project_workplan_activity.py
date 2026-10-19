from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, flt

from qfap_adds.qfap_adds.project_management.api import validate_project_team_employee
from qfap_adds.qfap_adds.project_management.services.workplan_sync import sync_activity_task, validate_activity_deletion


from qfap_adds.qfap_adds.project_management.services.project_reconciliation import reconcile_document_projects, reconcile_deleted_document, reconcile_project
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
        if output.status == "Inactive":
            frappe.throw(_("Inactive Project Outputs cannot be used."))
        if not output.sector:
            frappe.throw(_("The selected Project Output does not have a Sector."))
        self.sector = output.sector
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
        self.responsible_department = validate_project_team_employee(
            self.project,
            self.responsible_employee,
            "Responsible Employee",
        )

    def _set_lock_and_health(self):
        self.activity_locked=1 if self.status in ("Approved","Completed","Inactive","Cancelled") else 0
        if self.status == "Completed": self.activity_health="Completed"
        elif self.status == "On Hold": self.activity_health="On Hold"


def _qorg_reconcile_on_update(self):
    reconcile_document_projects(self)

def _qorg_reconcile_after_delete(self):
    reconcile_deleted_document(self)

def _qorg_reconcile_on_cancel(self):
    reconcile_document_projects(self)

def _qorg_reconcile_on_update_after_submit(self):
    reconcile_document_projects(self)

_qorg_original_on_update = getattr(ProjectWorkplanActivity, "on_update", None)
def _qorg_wrapped_on_update(self):
    if _qorg_original_on_update:
        _qorg_original_on_update(self)
    reconcile_document_projects(self)
ProjectWorkplanActivity.on_update = _qorg_wrapped_on_update

_qorg_original_after_delete = getattr(ProjectWorkplanActivity, "after_delete", None)
def _qorg_wrapped_after_delete(self):
    if _qorg_original_after_delete:
        _qorg_original_after_delete(self)
    reconcile_deleted_document(self)
ProjectWorkplanActivity.after_delete = _qorg_wrapped_after_delete

_qorg_original_on_cancel = getattr(ProjectWorkplanActivity, "on_cancel", None)
def _qorg_wrapped_on_cancel(self):
    if _qorg_original_on_cancel:
        _qorg_original_on_cancel(self)
    reconcile_document_projects(self)
ProjectWorkplanActivity.on_cancel = _qorg_wrapped_on_cancel

_qorg_original_on_update_after_submit = getattr(ProjectWorkplanActivity, "on_update_after_submit", None)
def _qorg_wrapped_on_update_after_submit(self):
    if _qorg_original_on_update_after_submit:
        _qorg_original_on_update_after_submit(self)
    reconcile_document_projects(self)
ProjectWorkplanActivity.on_update_after_submit = _qorg_wrapped_on_update_after_submit
