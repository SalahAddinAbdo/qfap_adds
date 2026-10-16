import frappe
from qfap_adds.qfap_adds.task_management.services import rebuild

def execute():
    for name in frappe.get_all("Task",filters={"is_group":1},pluck="name",limit_page_length=100000):rebuild(name)
