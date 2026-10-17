from __future__ import annotations
import frappe
from frappe import _
from frappe.utils import flt
def validate_project_link(doc, fieldname, linked_doctype):
    value=doc.get(fieldname)
    if not value:return
    project=frappe.db.get_value(linked_doctype,value,"project")
    if project and project != doc.project: frappe.throw(_("{0} must belong to the selected Project.").format(_(fieldname.replace("_"," ").title())))
def validate_dates(start_date,end_date,start_label="Start Date",end_label="End Date"):
    if start_date and end_date and end_date < start_date: frappe.throw(_("{0} cannot be before {1}.").format(_(end_label),_(start_label)))
def validate_percent(value,label):
    if flt(value)<0 or flt(value)>100: frappe.throw(_("{0} must be between 0 and 100.").format(_(label)))
