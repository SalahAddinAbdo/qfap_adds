from __future__ import annotations

import frappe
from frappe import _


@frappe.whitelist()
def get_project_team_employees(project: str | None = None):
    """Return active Employees assigned to the Project Core Team.

    This endpoint is the shared source for all project-cycle Employee link
    fields whose assignee must belong to the selected Project team.
    """
    project = (project or "").strip()
    if not project:
        return []
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} was not found.").format(frappe.bold(project)))
    if not frappe.has_permission("Project", "read", project):
        frappe.throw(_("You are not permitted to access this Project."), frappe.PermissionError)

    rows = frappe.get_all(
        "Project Core Team Assignment",
        filters={
            "parent": project,
            "parenttype": "Project",
            "parentfield": "custom_project_core_team",
            "active": 1,
        },
        pluck="employee",
        order_by="idx asc",
        limit_page_length=0,
    )
    employees = []
    for employee in rows:
        if not employee or employee in employees:
            continue
        if frappe.db.get_value("Employee", employee, "status") == "Active":
            employees.append(employee)
    return employees


def validate_project_team_employee(project: str, employee: str, label: str = "Responsible Employee"):
    """Validate that an Employee is active and assigned to the Project team."""
    if not employee:
        frappe.throw(_("{0} is required.").format(_(label)))

    status = frappe.db.get_value("Employee", employee, "status")
    if status != "Active":
        frappe.throw(_("{0} must be an active Employee.").format(_(label)))

    assigned = frappe.db.exists(
        "Project Core Team Assignment",
        {
            "parent": project,
            "parenttype": "Project",
            "parentfield": "custom_project_core_team",
            "employee": employee,
            "active": 1,
        },
    )
    if not assigned:
        frappe.throw(
            _("{0} must be an active member of the selected Project Core Team.").format(
                _(label)
            )
        )

    return frappe.db.get_value("Employee", employee, "department") or ""
