from __future__ import annotations

import frappe

from qfap_adds.qfap_adds.task_management.settings import (
    get_global_reopen_roles,
    get_settings,
)
from qfap_adds.qfap_adds.task_management.services import rebuild, rebuild_chain

@frappe.whitelist()
def task_assignment_scope(target_employee=None):
    settings = get_settings()
    if not int(settings.enabled or 0):
        frappe.throw("Task integration is disabled in Task Management Settings.")
    # =========================================================
    # API Server Script: task_assignment_scope
    # Version: 1.3 STRICT REPORTS_TO HIERARCHY
    # Frappe / ERPNext 16 Safe Execution
    # =========================================================

    current_user = frappe.session.user
    requested_target = target_employee or ""

    # Administrator remains the only global exception.
    # System Manager and HR Manager still follow the Employee reporting tree.
    privileged = current_user == "Administrator"

    current_employee = ""
    current_company = ""

    current_rows = frappe.db.get_all(
        "Employee",
        filters={"user_id": current_user, "status": "Active"},
        fields=["name", "company"],
        order_by="modified desc",
        limit_page_length=1
    )

    if current_rows:
        current_employee = current_rows[0].get("name") or ""
        current_company = current_rows[0].get("company") or ""

    if not current_employee and not privileged:
        frappe.throw(
            "Your user account is not linked to an active Employee record. "
            "Please contact the System Administrator."
        )

    employee_rows = frappe.db.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "company", "reports_to"],
        order_by="employee_name asc"
    )

    assignees = []

    if privileged:
        for employee_row in employee_rows:
            employee_name = employee_row.get("name")
            if employee_name and employee_name not in assignees:
                assignees.append(employee_name)
    else:
        # Start with the current employee, then walk downward only through
        # exact reports_to relationships. No lft/rgt range is used.
        assignees.append(current_employee)
        hierarchy_changed = True
        hierarchy_pass = 0

        while hierarchy_changed and hierarchy_pass < 100:
            hierarchy_changed = False
            hierarchy_pass = hierarchy_pass + 1

            for employee_row in employee_rows:
                employee_name = employee_row.get("name")
                supervisor_name = employee_row.get("reports_to") or ""
                employee_company = employee_row.get("company") or ""

                same_company = True
                if current_company and employee_company:
                    same_company = employee_company == current_company

                if (
                    employee_name
                    and same_company
                    and supervisor_name in assignees
                    and employee_name not in assignees
                ):
                    assignees.append(employee_name)
                    hierarchy_changed = True

    # Valid Task Assigned By values for the selected assignee:
    # selected employee + every supervisor above the employee.
    selected_employee = requested_target or current_employee
    supervisors = []

    if selected_employee:
        supervisors.append(selected_employee)
        next_supervisor = frappe.db.get_value(
            "Employee",
            selected_employee,
            "reports_to"
        ) or ""
        supervisor_guard = 0

        while next_supervisor and supervisor_guard < 100:
            supervisor_guard = supervisor_guard + 1

            if next_supervisor in supervisors:
                break

            supervisors.append(next_supervisor)
            next_supervisor = frappe.db.get_value(
                "Employee",
                next_supervisor,
                "reports_to"
            ) or ""

    can_manage_selected = privileged
    if not can_manage_selected and requested_target:
        if requested_target != current_employee and requested_target in assignees:
            can_manage_selected = True

    result = {
        "current_employee": current_employee,
        "assignees": assignees,
        "supervisors": supervisors,
        "privileged": 1 if privileged else 0,
        "can_manage_selected": 1 if can_manage_selected else 0,
        "assignable_employee_names": assignees,
        "supervisor_names": supervisors,
        "target_employee": requested_target,
        "target_allowed": 1 if requested_target and requested_target in assignees else 0
    }

    return result

@frappe.whitelist()
def task_project_workplan_parent_options(project=None, current_task=None):
    settings = get_settings()
    if not int(settings.enabled or 0):
        return {"project": project or "", "options": []}
    project = project or ""
    current_task = current_task or ""
    if not project or not frappe.db.exists("Project", project):
        return {"project": project, "options": []}

    current_user = frappe.session.user
    current_employee = frappe.db.get_value(
        "Employee", {"user_id": current_user, "status": "Active"}, "name"
    ) or ""

    shared_task_names = set(
        frappe.get_all(
            "DocShare",
            filters={"user": current_user, "share_doctype": "Task", "read": 1},
            pluck="share_name",
            limit_page_length=5000,
        )
    )

    # Exclude the current task and all its descendants to prevent circular trees.
    excluded = set([current_task]) if current_task else set()
    frontier = [current_task] if current_task else []
    guard = 0
    while frontier and guard < int(settings.hierarchy_max_depth or 100):
        guard += 1
        children = frappe.get_all(
            "Task", filters={"parent_task": ["in", frontier]}, pluck="name",
            limit_page_length=5000,
        )
        frontier = [name for name in children if name and name not in excluded]
        excluded.update(frontier)

    rows = frappe.get_all(
        "Task",
        filters={
            "project": project,
            "is_group": 1,
            "custom_task_locked": 0,
            "status": ["not in", ["Completed", "Cancelled", "Template"]],
        },
        fields=[
            "name", "subject", "owner", "status", "priority", "progress",
            "exp_start_date", "exp_end_date", "expected_time", "actual_time",
            "custom_project_workplan", "custom_assign_to",
            "custom_child_task_count", "custom_completed_child_task_count",
        ],
        order_by="custom_project_workplan desc, priority desc, subject asc",
        limit_page_length=2000,
    )

    options = []
    for row in rows:
        task_name = row.get("name") or ""
        if not task_name or task_name in excluded:
            continue
        is_workplan = int(row.get("custom_project_workplan") or 0) == 1
        personal_allowed = bool(
            row.get("owner") == current_user
            or (current_employee and row.get("custom_assign_to") == current_employee)
            or task_name in shared_task_names
        )
        if is_workplan and not int(settings.allow_workplan_as_parent or 0):
            continue
        if not (is_workplan or personal_allowed or current_user == "Administrator"):
            continue

        category = "Project Workplan" if is_workplan else "My Main Task"
        subject = row.get("subject") or task_name
        child_count = int(row.get("custom_child_task_count") or 0)
        completed_count = int(row.get("custom_completed_child_task_count") or 0)
        details = [category, subject, task_name, row.get("status") or ""]
        if row.get("priority"):
            details.append(row.get("priority"))
        if child_count:
            details.append(str(completed_count) + "/" + str(child_count) + " children")
        options.append({
            "label": " | ".join([str(value) for value in details if value]),
            "value": task_name,
            "category": category,
            "subject": subject,
            "status": row.get("status") or "",
            "priority": row.get("priority") or "",
            "start_date": str(row.get("exp_start_date") or ""),
            "end_date": str(row.get("exp_end_date") or ""),
            "progress": float(row.get("progress") or 0),
            "expected_time": float(row.get("expected_time") or 0),
            "actual_time": float(row.get("actual_time") or 0),
            "child_count": child_count,
            "completed_child_count": completed_count,
        })

    return {"project": project, "options": options}


@frappe.whitelist()
def reopen_task(task=None):
    # =========================================================
    # API Server Script: reopen_task
    # Frappe / ERPNext 16 Safe Execution
    #
    # Permission model:
    # 1. Administrator, System Manager, and HR Manager:
    #    may reopen any eligible task.
    # 2. Manager role:
    #    may reopen only a task assigned to the manager's own
    #    Employee record or to an employee below that manager.
    # 3. All other users:
    #    are not allowed by this API.
    # =========================================================

    current_user = frappe.session.user
    settings = get_settings()
    manager_role = settings.administrative_role or "Task Management Administrator"

    task_name = task or ""
    if not task_name:
        frappe.throw("Task is required.")

    # ---------------------------------------------------------
    # Load current user's roles
    # ---------------------------------------------------------
    roles = []

    if current_user == "Administrator":
        roles = ["Administrator", "System Manager"]
    else:
        role_rows = frappe.db.get_all(
            "Has Role",
            filters={
                "parent": current_user,
                "parenttype": "User"
            },
            fields=["role"]
        )

        for role_row in role_rows:
            role_name = role_row.get("role") or ""
            if role_name and role_name not in roles:
                roles.append(role_name)

    # ---------------------------------------------------------
    # Global roles may reopen any eligible task
    # ---------------------------------------------------------
    privileged = current_user == "Administrator"

    for global_role in [x.strip() for x in str(settings.global_reopen_roles or "").splitlines() if x.strip()]:
        if global_role in roles:
            privileged = True

    # The Manager role is deliberately scoped, not global.
    scoped_manager = manager_role in roles

    # ---------------------------------------------------------
    # Load current Employee record
    # ---------------------------------------------------------
    current_employee = ""
    current_lft = 0
    current_rgt = 0

    current_rows = frappe.db.get_all(
        "Employee",
        filters={
            "user_id": current_user,
            "status": "Active"
        },
        fields=["name", "lft", "rgt"],
        limit_page_length=1
    )

    if current_rows:
        current_employee = current_rows[0].get("name") or ""
        current_lft = int(current_rows[0].get("lft") or 0)
        current_rgt = int(current_rows[0].get("rgt") or 0)

    # A scoped Manager must have an active Employee linked to the user.
    if not privileged and scoped_manager and not current_employee:
        frappe.throw("No active Employee record is linked to your user account.")

    # ---------------------------------------------------------
    # Load task
    # custom_assign_to is expected to contain an Employee name.
    # ---------------------------------------------------------
    task_values = frappe.db.get_value(
        "Task",
        task_name,
        ["status", "custom_task_locked", "custom_assign_to", "parent_task"],
        as_dict=True
    )

    if not task_values:
        frappe.throw("Task not found.")

    # ---------------------------------------------------------
    # Authorization
    # ---------------------------------------------------------
    allowed = privileged
    assigned_employee = task_values.get("custom_assign_to") or ""

    if not allowed and scoped_manager and current_employee and assigned_employee:
        # A manager may reopen their own assigned task.
        if assigned_employee == current_employee:
            allowed = True

        # Otherwise, allow only employees below the manager.
        if not allowed:
            target = frappe.db.get_value(
                "Employee",
                assigned_employee,
                ["lft", "rgt", "reports_to"],
                as_dict=True
            )

            if target:
                target_lft = int(target.get("lft") or 0)
                target_rgt = int(target.get("rgt") or 0)

                # Fast hierarchy check when Nested Set values are available.
                if (
                    current_lft > 0
                    and current_rgt > current_lft
                    and target_lft > current_lft
                    and target_rgt < current_rgt
                ):
                    allowed = True

                # Fallback and consistency check through reports_to chain.
                if not allowed:
                    next_supervisor = target.get("reports_to") or ""
                    supervisor_guard = 0

                    while next_supervisor and supervisor_guard < 100:
                        supervisor_guard = supervisor_guard + 1

                        if next_supervisor == current_employee:
                            allowed = True
                            break

                        next_supervisor = frappe.db.get_value(
                            "Employee",
                            next_supervisor,
                            "reports_to"
                        ) or ""

    if not allowed:
        frappe.throw("You are not authorized to reopen this task.")

    # ---------------------------------------------------------
    # Reopening conditions
    # ---------------------------------------------------------
    if (
        task_values.get("status") != "Completed"
        or int(task_values.get("custom_task_locked") or 0) != 1
    ):
        frappe.throw("Only completed and locked tasks can be reopened.")

    # ---------------------------------------------------------
    # Reopen task
    # ---------------------------------------------------------
    frappe.db.set_value(
        "Task",
        task_name,
        {
            "status": "Working",
            "custom_task_locked": 0,
            "completed_on": None,
            "completed_by": None,
            "closing_date": None
        },
        update_modified=True
    )

    parent_task = task_values.get("parent_task") or ""
    if parent_task:
        rebuild_chain(parent_task)

    comment_doc = frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "Task",
        "reference_name": task_name,
        "content": "Task reopened by " + current_user
    })
    comment_doc.insert(ignore_permissions=True)

    result = {
        "task": task_name,
        "status": "Working"
    }

    return result

@frappe.whitelist()
def task_unlock_parent_summary(task=None):
    # =========================================================
    # API: task_unlock_parent_summary
    # Frappe / ERPNext 16 Safe Execution
    # =========================================================

    task_name = task or ""
    if not task_name:
        frappe.throw("Task is required.")

    current_user = frappe.session.user
    current_employee = frappe.db.get_value(
        "Employee",
        {"user_id": current_user, "status": "Active"},
        "name"
    ) or ""

    values = frappe.db.get_value(
        "Task",
        task_name,
        ["owner", "custom_assign_to", "custom_child_task_count"],
        as_dict=True
    )
    if not values:
        frappe.throw("Task not found.")

    allowed = current_user == "Administrator" or values.get("owner") == current_user

    if not allowed and current_employee and values.get("custom_assign_to"):
        cursor = values.get("custom_assign_to")
        guard = 0
        while cursor and guard < 100:
            guard = guard + 1
            if cursor == current_employee:
                allowed = True
                break
            cursor = frappe.db.get_value("Employee", cursor, "reports_to") or ""

    if not allowed:
        frappe.throw("You are not authorized to enable manual editing for this main task.")

    if int(values.get("custom_child_task_count") or 0) < 1:
        frappe.throw("This task has no active child tasks.")

    frappe.db.set_value(
        "Task",
        task_name,
        "custom_parent_rollup_locked",
        0,
        update_modified=True
    )

    comment = frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "Task",
        "reference_name": task_name,
        "content": "Manual editing enabled for the main task by " + current_user
    })
    comment.insert(ignore_permissions=True)

    result = {"task": task_name, "unlocked": 1}

    return result

@frappe.whitelist()
def task_complete_parent_summary(task=None):
    # =========================================================
    # API: task_complete_parent_summary
    # Frappe / ERPNext 16 Safe Execution
    # Marks a main task Completed only after every active child is complete.
    # =========================================================

    task_name = task or ""

    if not task_name:
        frappe.throw("Task is required.")

    current_user = frappe.session.user
    current_employee = frappe.db.get_value(
        "Employee",
        {"user_id": current_user, "status": "Active"},
        "name"
    ) or ""

    task_values = frappe.db.get_value(
        "Task",
        task_name,
        [
            "owner",
            "status",
            "custom_assign_to",
            "custom_task_locked",
            "custom_child_task_count"
        ],
        as_dict=True
    )

    if not task_values:
        frappe.throw("Task not found.")

    if int(task_values.get("custom_task_locked") or 0) == 1:
        frappe.throw("The main task is already completed and locked.")

    allowed = current_user == "Administrator" or task_values.get("owner") == current_user

    if not allowed and current_employee and task_values.get("custom_assign_to"):
        cursor = task_values.get("custom_assign_to")
        guard = 0

        while cursor and guard < 100:
            guard = guard + 1

            if cursor == current_employee:
                allowed = True
                break

            cursor = frappe.db.get_value(
                "Employee",
                cursor,
                "reports_to"
            ) or ""

    if not allowed:
        frappe.throw("You are not authorized to complete this main task.")

    children = frappe.db.get_all(
        "Task",
        filters={
            "parent_task": task_name,
            "status": ["not in", ["Cancelled", "Template"]]
        },
        fields=["name", "status"],
        limit_page_length=5000
    )

    if not children:
        frappe.throw("This task has no active child tasks.")

    incomplete_count = 0

    for child in children:
        if child.get("status") != "Completed":
            incomplete_count = incomplete_count + 1

    if incomplete_count:
        frappe.throw(
            "All active child tasks must be completed before completing the main task."
        )

    rollup_values = rebuild(task_name)

    frappe.db.set_value(
        "Task",
        task_name,
        {
            "status": "Completed",
            "progress": 100,
            "completed_on": frappe.utils.today(),
            "completed_by": current_user,
            "closing_date": frappe.utils.today(),
            "custom_task_locked": 1,
            "custom_parent_rollup_locked": 1,
            "custom_child_task_count": len(children),
            "custom_completed_child_task_count": len(children),
            "expected_time": rollup_values.get("expected_time", 0),
            "actual_time": rollup_values.get("actual_time", 0),
            "exp_end_date": rollup_values.get("exp_end_date"),
            "custom_expected_days": rollup_values.get("custom_expected_days", 0)
        },
        update_modified=True
    )

    comment = frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "Task",
        "reference_name": task_name,
        "content": "Main task completed from the controlled action by " + current_user
    })
    comment.insert(ignore_permissions=True)

    result = {
        "task": task_name,
        "status": "Completed",
        "completed_children": len(children)
    }

    return result

