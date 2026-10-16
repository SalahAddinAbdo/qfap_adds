from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address


class TaskManagementSettings(Document):
    def validate(self):
        self._validate_roles()
        self._validate_recipients()
        self._validate_schedule()
        self._set_next_send()

    def _validate_roles(self):
        seen = set()
        for row in self.global_reopen_role_rows or []:
            if not row.enabled:
                continue
            if row.role in seen:
                frappe.throw(_("Role {0} is duplicated.").format(row.role))
            seen.add(row.role)

    def _validate_recipients(self):
        seen = set()
        for row in self.summary_recipients or []:
            if not row.enabled:
                continue
            email = ""
            if row.recipient_type == "System User":
                if not row.user:
                    frappe.throw(_("System User is required in recipient row {0}.").format(row.idx))
                user = frappe.db.get_value("User", row.user, ["enabled", "email"], as_dict=True)
                if not user or not user.enabled or not user.email:
                    frappe.throw(_("Recipient User {0} must be enabled and have an email address.").format(row.user))
                row.external_email = None
                email = user.email
            elif row.recipient_type == "External Email":
                row.user = None
                email = (row.external_email or "").strip()
                if not validate_email_address(email, throw=False):
                    frappe.throw(_("Invalid external email in recipient row {0}.").format(row.idx))
            else:
                frappe.throw(_("Select a valid Recipient Type in row {0}.").format(row.idx))
            key = email.lower()
            if key in seen:
                frappe.throw(_("Recipient email {0} is duplicated.").format(email))
            seen.add(key)

    def _validate_schedule(self):
        if not self.summary_schedule_enabled:
            return
        if self.summary_frequency not in ("Daily", "Weekly", "Monthly"):
            frappe.throw(_("Select Daily, Weekly, or Monthly frequency."))
        if not self.summary_send_time:
            frappe.throw(_("Send Time is required."))
        if self.summary_frequency == "Weekly" and not self.summary_weekly_day:
            frappe.throw(_("Weekly Send Day is required."))
        if self.summary_frequency == "Monthly" and not 1 <= int(self.summary_monthly_day or 0) <= 28:
            frappe.throw(_("Monthly Send Day must be between 1 and 28."))

    def _set_next_send(self):
        if not self.summary_schedule_enabled:
            self.summary_next_send_on = None
            return
        from qfap_adds.qfap_adds.task_management.scheduler import get_next_send_datetime
        self.summary_next_send_on = get_next_send_datetime(self)
