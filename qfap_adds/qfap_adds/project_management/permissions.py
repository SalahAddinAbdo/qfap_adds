from __future__ import annotations
import frappe

def _employee(user):
    return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")

def _projects(user):
    if user == "Administrator" or "System Manager" in frappe.get_roles(user): return None
    employee=_employee(user)
    if not employee: return []
    projects=frappe.get_all("Project Core Team Assignment",filters={"employee":employee,"active":1,"parenttype":"Project","parentfield":"custom_project_core_team"},pluck="parent",limit_page_length=0)
    meta=frappe.get_meta("Project")
    if meta.has_field("custom_project_manager"): projects += frappe.get_all("Project",filters={"custom_project_manager":employee},pluck="name",limit_page_length=0)
    return sorted(set(projects))

def _condition(doctype,user=None):
    projects=_projects(user or frappe.session.user)
    if projects is None: return ""
    if not projects: return "1=0"
    values=", ".join(frappe.db.escape(x) for x in projects)
    return f"`tab{doctype}`.`project` in ({values})"

def _has(doc,user=None,permission_type=None):
    projects=_projects(user or frappe.session.user)
    return True if projects is None else bool(doc.get("project") in projects)

def project_result_query(user=None):
    return _condition('Project Result', user)

def project_result_has(doc,user=None,permission_type=None):
    return _has(doc,user,permission_type)

def project_indicator_query(user=None):
    return _condition('Project Indicator', user)

def project_indicator_has(doc,user=None,permission_type=None):
    return _has(doc,user,permission_type)

def indicator_target_plan_query(user=None):
    return _condition('Indicator Target Plan', user)

def indicator_target_plan_has(doc,user=None,permission_type=None):
    return _has(doc,user,permission_type)

def project_workplan_activity_query(user=None):
    return _condition('Project Workplan Activity', user)

def project_workplan_activity_has(doc,user=None,permission_type=None):
    return _has(doc,user,permission_type)

def project_progress_update_query(user=None):
    return _condition('Project Progress Update', user)

def project_progress_update_has(doc,user=None,permission_type=None):
    return _has(doc,user,permission_type)

def project_risk_query(user=None):
    return _condition('Project Risk', user)

def project_risk_has(doc,user=None,permission_type=None):
    return _has(doc,user,permission_type)

def project_change_request_query(user=None):
    return _condition('Project Change Request', user)

def project_change_request_has(doc,user=None,permission_type=None):
    return _has(doc,user,permission_type)

def project_compliance_deliverable_query(user=None):
    return _condition('Project Compliance Deliverable', user)

def project_compliance_deliverable_has(doc,user=None,permission_type=None):
    return _has(doc,user,permission_type)

def project_beneficiary_plan_query(user=None):
    return _condition('Project Beneficiary Plan', user)

def project_beneficiary_plan_has(doc,user=None,permission_type=None):
    return _has(doc,user,permission_type)

def project_closure_query(user=None):
    return _condition('Project Closure', user)

def project_closure_has(doc,user=None,permission_type=None):
    return _has(doc,user,permission_type)
