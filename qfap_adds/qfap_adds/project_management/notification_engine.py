from __future__ import annotations

import frappe
from frappe.utils import add_days, getdate, nowdate

DATE_FIELDS={
 "risk_review_overdue":["next_review_date","review_due_date","risk_review_date"],
 "deliverable_due_soon":["submission_due_date","due_date"],
 "deliverable_overdue":["submission_due_date","due_date"],
 "change_pending_implementation":["implementation_due_date","planned_implementation_date","target_implementation_date"],
 "closure_action_overdue":["follow_up_end_date","closure_due_date"],
 "progress_update_overdue":["next_update_date","reporting_period_end","update_due_date"],
}
CLOSED_VALUES={"Approved","Completed","Closed","Cancelled","Waived","Rejected","Implemented","Finalized"}


def _field(meta,candidates):
    for name in candidates:
        if meta.has_field(name): return name
    return None


def _recipients(rule,doc):
    users=set()

    # Explicit users have the highest priority and support multiple recipients.
    for row in rule.get("recipient_users") or []:
        if row.enabled and row.user:
            users.add(row.user)

    # Employees are resolved through Employee.user_id.
    for row in rule.get("recipient_employees") or []:
        if not row.enabled or not row.employee:
            continue
        user=frappe.db.get_value("Employee",row.employee,"user_id")
        if user:
            users.add(user)

    # Backward compatibility with the earlier single Employee custom field.
    legacy_employee=rule.get("recipient_employee")
    if legacy_employee and frappe.db.exists("Employee",legacy_employee):
        user=frappe.db.get_value("Employee",legacy_employee,"user_id")
        if user:
            users.add(user)

    if rule.recipient_role:
        for user in frappe.get_all("Has Role",filters={"role":rule.recipient_role,"parenttype":"User"},pluck="parent"):
            if user and user != "Guest":
                users.add(user)

    if not users and rule.fallback_to_project_manager and doc.get("project"):
        meta=frappe.get_meta("Project")
        for candidate in ("project_manager","custom_project_manager","manager"):
            if not meta.has_field(candidate):
                continue
            value=frappe.db.get_value("Project",doc.project,candidate)
            if value:
                if frappe.db.exists("User",value):
                    users.add(value)
                elif frappe.db.exists("Employee",value):
                    user=frappe.db.get_value("Employee",value,"user_id")
                    if user:
                        users.add(user)
            break

    return [
        user for user in users
        if frappe.db.exists("User",user) and frappe.db.get_value("User",user,"enabled")
    ]


def _template(rule,doc):
    subject=(rule.rule_label or rule.notification_key)+" - "+doc.name
    message=rule.description or subject
    if rule.notification_record and frappe.db.exists("Notification",rule.notification_record):
        template=frappe.get_doc("Notification",rule.notification_record)
        context={"doc":doc}
        try:
            subject=frappe.render_template(template.subject or subject,context)
            message=frappe.render_template(template.message or message,context)
        except Exception:
            pass
    return subject,message


def _already_sent(user,subject):
    return frappe.db.exists("Notification Log",{"for_user":user,"subject":subject,"creation":[">=",nowdate()]})


def _send(rule,doc):
    users=_recipients(rule,doc)
    if not users:
        return 0
    subject,message=_template(rule,doc)
    count=0
    for user in users:
        if _already_sent(user,subject): continue
        frappe.get_doc({"doctype":"Notification Log","subject":subject,"email_content":message,"for_user":user,"from_user":frappe.session.user or "Administrator","type":"Alert","document_type":doc.doctype,"document_name":doc.name}).insert(ignore_permissions=True)
        if rule.delivery_channel=="Email and System Notification":
            email=frappe.db.get_value("User",user,"email")
            if email: frappe.sendmail(recipients=[email],subject=subject,message=message,delayed=True)
        count+=1
    return count


def _matches(rule,doc,today):
    meta=doc.meta
    key=rule.notification_key
    status_field=_field(meta,["monitoring_status","status","workflow_state"])
    status=doc.get(status_field) if status_field else ""
    if status in CLOSED_VALUES: return False
    date_field=_field(meta,DATE_FIELDS.get(key,[]))
    if not date_field or not doc.get(date_field): return False
    due=getdate(doc.get(date_field)); days=int(rule.due_soon_days or 0)
    if key=="deliverable_due_soon": return today <= due <= add_days(today,days)
    return due < today or (days and due <= add_days(today,-days))


def run_daily_project_notifications():
    if not frappe.db.exists("DocType","Projects Settings"): return
    settings=frappe.get_single("Projects Settings")
    today=getdate(nowdate())
    for rule in settings.get("project_notification_rules") or []:
        if not rule.enabled or rule.trigger_type!="Daily" or not rule.reference_doctype or not frappe.db.exists("DocType",rule.reference_doctype): continue
        for name in frappe.get_all(rule.reference_doctype,pluck="name",limit_page_length=0):
            doc=frappe.get_doc(rule.reference_doctype,name)
            if _matches(rule,doc,today): _send(rule,doc)


def process_project_notification_on_update(doc,method=None):
    if doc.doctype!="Project Risk" or not frappe.db.exists("DocType","Projects Settings"): return
    settings=frappe.get_single("Projects Settings")
    rule=next((r for r in settings.get("project_notification_rules") or [] if r.notification_key=="critical_risk" and r.enabled),None)
    if not rule: return
    field=_field(doc.meta,["risk_level","risk_rating","severity","priority"])
    value=str(doc.get(field) or "") if field else ""
    if value in ("High","Critical"): _send(rule,doc)
