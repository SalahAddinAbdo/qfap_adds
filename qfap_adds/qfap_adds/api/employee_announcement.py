from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.utils import now_datetime

EMAIL_TEMPLATE = "New Employee Announcement - Bilingual"
ALLOWED_ROLES = {"HR User", "HR Manager", "System Manager"}


@frappe.whitelist()
def send_new_employee_announcement(
    employee,
    action="send",
    recipients=None,
    cc=None,
    reply_to=None,
    additional_message=None,
):
    _check_access()
    doc = frappe.get_doc("Employee", employee)
    _validate_employee(doc)
    sender = _get_sender()
    defaults, default_cc = _default_recipients(doc)
    suggested_reply_to = frappe.session.user if _valid_email(frappe.session.user) else sender.email_id
    if (action or "send").strip().lower() == "preview":
        return {
            "success": 1,
            "recipients": defaults,
            "cc": default_cc,
            "recipient_count": len(defaults),
            "cc_count": len(default_cc),
            "new_employee_email": doc.user_id or doc.company_email or doc.personal_email or "",
            "sender_email": sender.email_id,
            "sender_account": sender.name,
            "suggested_reply_to": suggested_reply_to,
        }
    if doc.custom_welcome_email_sent_for_joining_date == doc.date_of_joining:
        frappe.throw(_("The announcement was already sent for this joining date."))
    to_list = _parse_emails(recipients)
    cc_list = _parse_emails(cc)
    if not to_list:
        frappe.throw(_("At least one recipient is required."))
    reply_to = (reply_to or suggested_reply_to).strip()
    if reply_to and not _valid_email(reply_to):
        frappe.throw(_("Invalid Reply-To email address."))
    if not frappe.db.exists("Email Template", EMAIL_TEMPLATE):
        frappe.throw(_("Email Template not found: {0}").format(EMAIL_TEMPLATE))
    template = frappe.get_doc("Email Template", EMAIL_TEMPLATE)
    context = _context(doc, additional_message or "")
    subject = frappe.render_template(template.subject or "", context)
    message = frappe.render_template(template.response_html or template.response or "", context)
    if not subject or not message:
        frappe.throw(_("The announcement email template is incomplete."))
    frappe.sendmail(
        recipients=to_list,
        cc=cc_list,
        sender=sender.email_id,
        reply_to=reply_to,
        subject=subject,
        message=message,
        reference_doctype="Employee",
        reference_name=doc.name,
        now=False,
    )
    frappe.db.set_value("Employee", doc.name, {
        "custom_welcome_email_sent_for_joining_date": doc.date_of_joining,
        "custom_welcome_email_sent_on": now_datetime(),
        "custom_welcome_email_sent_by": frappe.session.user,
    })
    return {
        "success": 1,
        "recipient_count": len(to_list),
        "cc_count": len(cc_list),
        "joining_date": str(doc.date_of_joining),
        "sender_email": sender.email_id,
        "sender_account": sender.name,
        "reply_to": reply_to,
    }


def _check_access():
    if frappe.session.user == "Administrator":
        return
    if not ALLOWED_ROLES.intersection(frappe.get_roles(frappe.session.user)):
        frappe.throw(_("Only HR User or HR Manager can send new employee announcements."), frappe.PermissionError)


def _validate_employee(doc):
    if doc.status != "Active":
        frappe.throw(_("The announcement can only be sent for an active employee."))
    if not doc.date_of_joining:
        frappe.throw(_("Date of Joining is required before sending the announcement."))
    if not doc.gender:
        frappe.throw(_("Gender must be specified before sending the announcement."))


def _get_sender():
    sender = None
    if _valid_email(frappe.session.user):
        sender = frappe.db.get_value("Email Account", {"email_id": frappe.session.user, "enable_outgoing": 1}, ["name", "email_id"], as_dict=True)
    if not sender:
        sender = frappe.db.get_value("Email Account", {"enable_outgoing": 1, "default_outgoing": 1}, ["name", "email_id"], as_dict=True)
    if not sender:
        frappe.throw(_("No enabled outgoing Email Account is configured."))
    return sender


def _default_recipients(new_employee):
    rows = frappe.get_all("Employee", filters={"status": "Active"}, fields=["user_id"], limit_page_length=0)
    new_email = new_employee.user_id or new_employee.company_email or new_employee.personal_email or ""
    to_list = []
    for row in rows:
        email = (row.user_id or "").strip()
        if email and email != new_email and email not in {"Administrator", "Guest"} and frappe.db.get_value("User", email, "enabled"):
            if email.lower() not in {x.lower() for x in to_list}:
                to_list.append(email)
    cc_list = [new_email] if _valid_email(new_email) else []
    return to_list, cc_list


def _parse_emails(raw):
    if isinstance(raw, (list, tuple)):
        values = raw
    else:
        values = re.split(r"[,;\n]+", raw or "")
    result = []
    for value in values:
        value = (value or "").strip()
        if not value:
            continue
        if not _valid_email(value):
            frappe.throw(_("Invalid email address: {0}").format(value))
        if value.lower() not in {x.lower() for x in result}:
            result.append(value)
    return result


def _valid_email(value):
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", value or ""))


def _context(doc, additional_message):
    male = str(doc.gender or "").strip().lower() in {"male", "ذكر"}
    return {
        "doc": doc,
        "employee": doc,
        "name": doc.name,
        "employee_name": doc.employee_name or "",
        "employee_number": doc.get("employee_number") or doc.name,
        "company": doc.company or "",
        "designation": doc.designation or "",
        "department": doc.department or "",
        "branch": doc.branch or "",
        "employment_type": doc.employment_type or "",
        "reports_to": doc.reports_to or "",
        "date_of_joining": doc.date_of_joining,
        "employee_bio": doc.bio or "",
        "additional_message": additional_message,
        "gender": doc.gender or "",
        "arabic_colleague": "الزميل" if male else "الزميلة",
        "arabic_new_colleague": "زميلنا الجديد" if male else "زميلتنا الجديدة",
        "arabic_welcome_object": "به" if male else "بها",
        "arabic_support_object": "له" if male else "لها",
        "arabic_possessive_journey": "مسيرته" if male else "مسيرتها",
        "arabic_success_object": "له" if male else "لها",
    }
