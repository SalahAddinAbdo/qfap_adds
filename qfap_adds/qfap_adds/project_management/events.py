from __future__ import annotations

import frappe

from qfap_adds.qfap_adds.project_management.services.workplan_sync import (
    sync_activity_task,
    validate_activity,
    validate_activity_deletion,
)


def validate_workplan_activity(doc, method=None):
    validate_activity(doc)


def sync_workplan_activity(doc, method=None):
    if getattr(doc.flags, "in_import", False) and frappe.flags.in_migrate:
        return
    sync_activity_task(doc.name)


def before_delete_workplan_activity(doc, method=None):
    validate_activity_deletion(doc)
