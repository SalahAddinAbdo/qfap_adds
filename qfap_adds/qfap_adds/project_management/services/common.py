from __future__ import annotations
import re
import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate
from qfap_adds.qfap_adds.project_management.api import validate_project_team_employee

_SCORE_RE = re.compile(r"^\s*([1-5])")

def numeric_rating(value):
    match = _SCORE_RE.match(str(value or ""))
    return int(match.group(1)) if match else 0

def validate_dates(start, end, start_label="Start Date", end_label="End Date"):
    if start and end and getdate(end) < getdate(start):
        frappe.throw(_("{0} cannot be before {1}.").format(_(end_label), _(start_label)))

def validate_project_link(project, doctype, name, label):
    if not name:
        return
    linked_project = frappe.db.get_value(doctype, name, "project")
    if linked_project and linked_project != project:
        frappe.throw(_("{0} must belong to the selected Project.").format(_(label)))

def validate_team_employee(project, employee, label):
    if not employee:
        return ""
    return validate_project_team_employee(project, employee, label)

def set_if_field(doc, fieldname, value):
    if doc.meta.has_field(fieldname):
        doc.set(fieldname, value)

def unique_child_rows(doc, table_field, key_fields, label):
    seen=set()
    for row in doc.get(table_field) or []:
        key=tuple(str(row.get(field) or "").strip() for field in key_fields)
        if not any(key):
            continue
        if key in seen:
            frappe.throw(_("Duplicate {0} row: {1}.").format(_(label), " / ".join(key)))
        seen.add(key)

def average_ratings(doc, fields):
    values=[numeric_rating(doc.get(field)) for field in fields]
    values=[value for value in values if value]
    return sum(values)/len(values) if values else 0

def today():
    return getdate(nowdate())
