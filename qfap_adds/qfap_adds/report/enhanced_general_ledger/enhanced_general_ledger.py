from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.general_ledger import general_ledger


def execute(filters=None):
    """Execute ERPNext General Ledger unchanged, then enrich presentation only."""
    result = list(general_ledger.execute(filters) or ([], []))
    while len(result) < 6:
        result.append(None)
    columns, data, message, chart, report_summary, skip_total_row = result[:6]
    columns = columns or []
    data = data or []
    _enhance_project_column(columns, data)
    report_summary = _build_audit_summary(data, report_summary)
    return columns, data, message, chart, report_summary, skip_total_row


def _enhance_project_column(columns, data):
    project_column = next((c for c in columns if c.get("fieldname") == "project"), None)
    if not project_column:
        return
    codes = sorted({r.get("project") for r in data if r.get("project")})
    names = {}
    if codes:
        names = {r.name: r.project_name for r in frappe.get_all("Project", filters={"name": ["in", codes]}, fields=["name", "project_name"], limit_page_length=0)}
    for row in data:
        code = row.get("project")
        if not code:
            continue
        title = names.get(code) or ""
        row["project_code"] = code
        row["project_name"] = title
        row["project"] = f"{code} - {title}" if title and title != code else code
    project_column.update({"label": _("Project"), "fieldtype": "Data", "width": 280})
    if not any(c.get("fieldname") == "project_code" for c in columns):
        columns.insert(columns.index(project_column) + 1, {"label": _("Project Code"), "fieldname": "project_code", "fieldtype": "Link", "options": "Project", "hidden": 1, "width": 130})


def _build_audit_summary(data, existing=None):
    details = [r for r in data if r.get("posting_date") and r.get("gl_entry")]
    vouchers = {(r.get("voucher_type"), r.get("voucher_no")) for r in details if r.get("voucher_no")}
    accounts = {r.get("account") for r in details if r.get("account")}
    projects = {r.get("project_code") for r in details if r.get("project_code")}
    missing = sum(1 for r in details if not r.get("project_code"))
    summary = list(existing or [])
    summary.extend([
        {"value": len(details), "label": _("GL Entries"), "datatype": "Int", "indicator": "blue"},
        {"value": len(vouchers), "label": _("Vouchers"), "datatype": "Int", "indicator": "blue"},
        {"value": len(accounts), "label": _("Accounts"), "datatype": "Int", "indicator": "blue"},
        {"value": len(projects), "label": _("Projects"), "datatype": "Int", "indicator": "blue"},
        {"value": missing, "label": _("Entries Without Project"), "datatype": "Int", "indicator": "orange" if missing else "green"},
        {"value": sum(flt(r.get("debit")) for r in details), "label": _("Detailed Debit"), "datatype": "Currency", "indicator": "green"},
        {"value": sum(flt(r.get("credit")) for r in details), "label": _("Detailed Credit"), "datatype": "Currency", "indicator": "orange"},
    ])
    return summary
