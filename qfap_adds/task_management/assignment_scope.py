from __future__ import annotations
import frappe
from qfap_adds.qfap_adds.task_management.settings import get_settings

def employee_for_user(user=None):
    user=user or frappe.session.user
    return frappe.db.get_value("Employee",{"user_id":user,"status":"Active"},"name") or ""

def descendants(employee, include_self=True):
    settings=get_settings(); rows=frappe.get_all("Employee",filters={"status":"Active"},fields=["name","reports_to","company"],limit_page_length=10000)
    company=frappe.db.get_value("Employee",employee,"company") if employee else None
    result=[employee] if employee and include_self else []; seen=set(result); frontier=[employee] if employee else []
    depth=0
    while frontier and depth<int(settings.hierarchy_max_depth or 100):
        depth+=1; nxt=[]
        for row in rows:
            if row.reports_to in frontier and row.name not in seen and (not settings.same_company_only or not company or row.company==company):
                seen.add(row.name); result.append(row.name); nxt.append(row.name)
        frontier=nxt
    return result

def supervisors(employee):
    settings=get_settings(); out=[]; seen=set(); cursor=employee
    for _ in range(int(settings.hierarchy_max_depth or 100)):
        cursor=frappe.db.get_value("Employee",cursor,"reports_to") or ""
        if not cursor or cursor in seen:break
        seen.add(cursor); out.append(cursor)
    return out

def can_manage_employee(target,user=None):
    user=user or frappe.session.user; settings=get_settings()
    if user=="Administrator" or settings.administrative_role in frappe.get_roles(user):return True
    current=employee_for_user(user)
    return bool(current and target in descendants(current,True))
