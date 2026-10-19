from __future__ import annotations

import frappe

from qfap_adds.qfap_adds.project_management.services.project_reconciliation import reconcile_project


def run_daily_project_reconciliation():
    result = {"checked": 0, "changed": 0}
    for project in frappe.get_all("Project", pluck="name", limit_page_length=0):
        row = reconcile_project(project)
        result["checked"] += 1
        if row.get("changed"):
            result["changed"] += 1
    return result
