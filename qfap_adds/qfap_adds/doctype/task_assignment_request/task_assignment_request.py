from __future__ import annotations

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, flt, getdate, now

from qfap_adds.qfap_adds.task_management.scope import can_manage_employee, employee_for_user
from qfap_adds.qfap_adds.task_management.services import validate_period, validate_request_duplicate, validate_task_tree
from qfap_adds.qfap_adds.task_management.settings import get_settings

DECISION_STATES = ("Approved", "Rejected")
LOCKED_STATES = ("Approved", "Rejected", "Applied", "Application Failed")


class TaskAssignmentRequest(Document):
    def before_insert(self):
        self.requested_by_user = frappe.session.user
        self.requested_by_employee = employee_for_user()
        self.requested_on = now()
        self.application_status = "Not Applied"
        self._set_employee_defaults()
        self._calculate_expected_values()

    def validate(self):
        self._set_employee_defaults()
        self._calculate_expected_values()
        self._validate_required_task_data()
        validate_request_duplicate(self)
        validate_task_tree(None, self.parent_task)
        validate_period(self.project, self.exp_start_date, self.exp_end_date, False, True)
        self._validate_decision_authority()
        self._protect_decided_request()

    def on_update(self):
        old = self.get_doc_before_save()
        old_state = old.workflow_state if old else None
        if self.workflow_state in DECISION_STATES and old_state != self.workflow_state:
            self.db_set("decision_by", frappe.session.user, update_modified=False)
            self.db_set("decision_on", now(), update_modified=False)
        if self.workflow_state == "Approved" and old_state != "Approved":
            self.apply_approved_request()

    def _set_employee_defaults(self):
        if not self.requested_assignee:
            return
        employee = frappe.db.get_value("Employee", self.requested_assignee, ["company", "status", "user_id"], as_dict=True)
        if not employee or employee.status != "Active":
            frappe.throw(_("The requested Employee must be active."))
        if not employee.user_id or not frappe.db.get_value("User", employee.user_id, "enabled"):
            frappe.throw(_("The requested Employee must be linked to an enabled User."))
        if not self.company:
            self.company = employee.company

    def _calculate_expected_values(self):
        if not self.exp_start_date or not self.exp_end_date:
            self.expected_days = 0
            return
        start_date = getdate(self.exp_start_date)
        end_date = getdate(self.exp_end_date)
        if end_date < start_date:
            frappe.throw(_("Expected End Date cannot be before Expected Start Date."))
        days = date_diff(end_date, start_date) + 1
        self.expected_days = flt(days, 2)
        if flt(self.expected_time) <= 0:
            settings = get_settings()
            self.expected_time = flt(days * flt(settings.working_hours_per_day or 8), 2)

    def _validate_required_task_data(self):
        if self.workflow_state not in ("Pending Approval", "Approved", "Applied"):
            return
        required = {
            "subject": _("Task Subject"), "requested_assignee": _("Employee"),
            "company": _("Company"), "project": _("Project"), "task_type": _("Task Type"),
            "priority": _("Priority"), "exp_start_date": _("Expected Start Date"),
            "exp_end_date": _("Expected End Date"), "expected_time": _("Expected Hours"),
            "request_reason": _("Request Reason"),
        }
        missing = [label for fieldname, label in required.items() if not self.get(fieldname)]
        if missing:
            frappe.throw(_("Complete these required fields before approval: {0}").format(", ".join(missing)))
        if flt(self.expected_time) <= 0:
            frappe.throw(_("Expected Hours must be greater than zero."))

    def _validate_decision_authority(self):
        old = self.get_doc_before_save()
        old_state = old.workflow_state if old else None
        if self.workflow_state not in DECISION_STATES or old_state == self.workflow_state:
            return
        settings = get_settings()
        if int(settings.prevent_self_approval or 0) and frappe.session.user == self.requested_by_user:
            frappe.throw(_("The requester cannot decide their own assignment request."))
        if not can_manage_employee(self.requested_assignee):
            frappe.throw(_("Only an authorized supervisor or Task Management Administrator can approve or reject this request."))

    def _protect_decided_request(self):
        old = self.get_doc_before_save()
        if not old or old.workflow_state not in LOCKED_STATES:
            return
        protected = ("subject", "description", "requested_assignee", "company", "task_type", "project", "parent_task", "priority", "exp_start_date", "exp_end_date", "expected_time", "request_reason")
        if any(str(old.get(field) or "") != str(self.get(field) or "") for field in protected):
            frappe.throw(_("A decided request cannot be changed."))

    def _application_fingerprint(self):
        raw = "|".join(str(value or "") for value in (self.name, self.company, self.task_type, self.project, self.parent_task, self.requested_assignee, self.subject, self.exp_start_date, self.exp_end_date))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def apply_approved_request(self):
        if self.created_task:
            return self.created_task
        if not can_manage_employee(self.requested_assignee):
            frappe.throw(_("You are not authorized to approve a task for this Employee."))
        fingerprint = self._application_fingerprint()
        duplicate = frappe.db.get_value("Task Assignment Request", {"application_fingerprint": fingerprint, "created_task": ["is", "set"], "name": ["!=", self.name]}, "name")
        if duplicate:
            frappe.throw(_("This approved request has already been applied in {0}.").format(duplicate))
        try:
            task = frappe.get_doc({
                "doctype": "Task", "company": self.company, "type": self.task_type,
                "subject": self.subject, "description": self.description, "project": self.project,
                "parent_task": self.parent_task, "priority": self.priority,
                "exp_start_date": self.exp_start_date, "exp_end_date": self.exp_end_date,
                "expected_time": self.expected_time, "custom_assign_to": self.requested_assignee,
                "custom_self_assigned": 0, "custom_task_assigned_by": employee_for_user(frappe.session.user),
                "custom_project_workplan": 0,
            })
            task.flags.from_assignment_request = True
            task.insert(ignore_permissions=True)
            self.db_set("created_task", task.name, update_modified=False)
            self.db_set("application_fingerprint", fingerprint, update_modified=False)
            self.db_set("application_status", "Applied", update_modified=False)
            self.db_set("application_error", "", update_modified=False)
            self.db_set("workflow_state", "Applied", update_modified=False)
            self.add_comment("Info", _("Task {0} was created automatically after approval.").format(task.name))
            return task.name
        except Exception:
            error = frappe.get_traceback()
            self.db_set("application_status", "Failed", update_modified=False)
            self.db_set("application_error", error, update_modified=False)
            self.db_set("workflow_state", "Application Failed", update_modified=False)
            frappe.log_error(error, "Task Assignment Request application failed: " + self.name)
            raise
