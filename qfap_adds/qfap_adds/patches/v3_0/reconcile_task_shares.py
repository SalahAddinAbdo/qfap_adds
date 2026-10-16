import frappe
from qfap_adds.qfap_adds.task_management.reconciliation import reconcile_all


def execute():
    batch_size = 500
    names = frappe.get_all("Task", pluck="name", order_by="creation asc", limit_page_length=1000000)
    for start in range(0, len(names), batch_size):
        for name in names[start:start + batch_size]:
            reconcile_all(dry_run=False, task=name, batch_size=1)
        frappe.db.commit()
