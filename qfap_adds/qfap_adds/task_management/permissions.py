from __future__ import annotations

import frappe

from qfap_adds.qfap_adds.task_management.assignment_scope import (
    can_manage_employee, descendants, employee_for_user,
)
from qfap_adds.qfap_adds.task_management.settings import get_settings

READ_TYPES = (None, "read", "select", "report", "print", "email")
WRITE_TYPES = ("write", "create")


def _admin(user):
    settings = get_settings()
    return user == "Administrator" or settings.administrative_role in frappe.get_roles(user)


def task_query_condition(user=None):
    user = user or frappe.session.user
    if _admin(user):
        return ""
    employee = employee_for_user(user)
    employees = descendants(employee, True) if employee else []
    employee_sql = ",".join(frappe.db.escape(value) for value in employees) or "''"
    user_sql = frappe.db.escape(user)
    return (
        "(`tabTask`.`owner`={u} OR `tabTask`.`custom_user_id`={u} "
        "OR `tabTask`.`custom_assign_to` IN ({e}) "
        "OR EXISTS (SELECT 1 FROM `tabDocShare` ds "
        "WHERE ds.share_doctype='Task' AND ds.share_name=`tabTask`.name "
        "AND ds.user={u} AND ds.read=1))"
    ).format(u=user_sql, e=employee_sql)


def has_task_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if _admin(user):
        return True
    if permission_type in ("delete", "cancel", "submit", "amend", "share"):
        return False
    employee = employee_for_user(user)
    in_scope = bool(employee and doc.get("custom_assign_to") in descendants(employee, True))
    shared_read = bool(frappe.db.exists(
        "DocShare", {"share_doctype": "Task", "share_name": doc.name, "user": user, "read": 1}
    ))
    if permission_type in READ_TYPES:
        return bool(doc.owner == user or doc.get("custom_user_id") == user or in_scope or shared_read)
    if permission_type in WRITE_TYPES:
        return bool(doc.owner == user or doc.get("custom_user_id") == user or in_scope)
    return None


def request_query_condition(user=None):
    user = user or frappe.session.user
    if _admin(user):
        return ""
    employee = employee_for_user(user)
    employees = descendants(employee, True) if employee else []
    employee_sql = ",".join(frappe.db.escape(value) for value in employees) or "''"
    return (
        "(`tabTask Assignment Request`.`requested_by_user`={u} "
        "OR `tabTask Assignment Request`.`requested_assignee` IN ({e}))"
    ).format(u=frappe.db.escape(user), e=employee_sql)


def has_request_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if _admin(user):
        return True
    is_requester = doc.requested_by_user == user
    can_supervise = can_manage_employee(doc.requested_assignee, user)
    if permission_type in READ_TYPES:
        return bool(is_requester or can_supervise)
    if permission_type in WRITE_TYPES:
        if doc.workflow_state in ("Draft", None, ""):
            return is_requester
        if doc.workflow_state == "Pending Approval":
            return can_supervise
        return False
    if permission_type in ("delete", "cancel"):
        return bool(is_requester and doc.workflow_state in ("Draft", None, ""))
    return None
