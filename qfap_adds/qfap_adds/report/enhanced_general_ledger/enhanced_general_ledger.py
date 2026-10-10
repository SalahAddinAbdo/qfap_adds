from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.general_ledger import general_ledger


def execute(filters=None):
    """Run ERPNext General Ledger, then add non-posting audit presentation."""
    filters = frappe._dict(filters or {})
    _validate_analytical_filters(filters)
    result = list(general_ledger.execute(filters) or ([], []))
    while len(result) < 6:
        result.append(None)
    columns, data, message, chart, report_summary, skip_total_row = result[:6]
    columns, data = columns or [], data or []
    dimensions = _get_active_dimensions()
    _enrich_link_dimensions(columns, data, dimensions)
    _add_audit_flags(columns, data, dimensions)
    data, subset_active = _apply_analytical_filters(data, filters)
    _apply_view(columns, filters.get("qfap_view") or "Standard")
    if filters.get("qfap_hide_empty_columns"):
        _hide_empty_optional_columns(columns, data)
    report_summary = _build_audit_summary(data, report_summary, dimensions)
    message = _build_message(message, subset_active)
    return columns, data, message, chart, report_summary, skip_total_row


def _validate_analytical_filters(filters):
    active = any(filters.get(f) for f in (
        "qfap_audit_search", "qfap_min_amount", "qfap_max_amount", "qfap_exceptions_only"
    ))
    if active and filters.get("categorize_by"):
        frappe.throw(_("QFap analytical filters cannot be combined with Categorize by. Clear Categorize by, then run the audit subset."))


def _get_active_dimensions():
    if not frappe.db.exists("DocType", "Accounting Dimension"):
        return []
    meta = frappe.get_meta("Accounting Dimension")
    fields = ["name", "label", "fieldname", "document_type"]
    filters = {}
    if meta.has_field("disabled"):
        fields.append("disabled")
        filters["disabled"] = 0
    return [d for d in frappe.get_all("Accounting Dimension", filters=filters, fields=fields, limit_page_length=0) if d.fieldname and d.document_type]


def _enrich_link_dimensions(columns, data, dimensions):
    specs = [
        frappe._dict(fieldname="project", document_type="Project", label=_("Project"), preferred_title_field="project_name", width=280),
        frappe._dict(fieldname="cost_center", document_type="Cost Center", label=_("Cost Center"), preferred_title_field="cost_center_name", width=240),
    ]
    known = {"project", "cost_center"}
    for d in dimensions:
        if d.fieldname not in known:
            specs.append(frappe._dict(fieldname=d.fieldname, document_type=d.document_type, label=d.label or d.fieldname, preferred_title_field=None, width=220))
    for spec in specs:
        column = next((c for c in columns if c.get("fieldname") == spec.fieldname), None)
        if not column:
            continue
        values = sorted({r.get(spec.fieldname) for r in data if r.get(spec.fieldname)})
        title_map = _get_title_map(spec.document_type, values, spec.preferred_title_field)
        code_field = f"qfap_{spec.fieldname}_code"
        title_field = f"qfap_{spec.fieldname}_title"
        for row in data:
            code = row.get(spec.fieldname)
            if not code:
                continue
            title = title_map.get(code) or ""
            row[code_field], row[title_field] = code, title
            row[spec.fieldname] = f"{code} - {title}" if title and title != code else code
        column.update({
            "label": _(spec.label), "fieldtype": "Data", "width": spec.width,
            "qfap_link_doctype": spec.document_type, "qfap_code_field": code_field,
            "qfap_title_field": title_field,
        })


def _get_title_map(document_type, values, preferred_title_field=None):
    if not values or not frappe.db.exists("DocType", document_type):
        return {}
    meta = frappe.get_meta(document_type)
    title_field = ""
    if preferred_title_field and meta.has_field(preferred_title_field):
        title_field = preferred_title_field
    elif meta.title_field and meta.has_field(meta.title_field):
        title_field = meta.title_field
    fields = ["name"] + ([title_field] if title_field else [])
    return {r.name: (r.get(title_field) if title_field else r.name) for r in frappe.get_all(document_type, filters={"name": ["in", values]}, fields=fields, limit_page_length=0)}


def _budget_fields(dimensions):
    result = []
    for d in dimensions:
        text = " ".join([d.fieldname or "", d.label or "", d.document_type or ""]).lower()
        if "budget" in text:
            result.append(d.fieldname)
    return result


def _add_audit_flags(columns, data, dimensions):
    budget_fields = _budget_fields(dimensions)
    for row in data:
        flags = []
        if _is_detail_row(row):
            if not row.get("project"):
                flags.append(_("Project not set"))
            if not row.get("cost_center"):
                flags.append(_("Cost Center not set"))
            if budget_fields and not any(row.get(f) for f in budget_fields):
                flags.append(_("Budget dimension not set"))
            if row.get("is_cancelled"):
                flags.append(_("Cancelled GL Entry"))
            if str(row.get("is_opening") or "").lower() == "yes":
                flags.append(_("Opening Entry"))
            if not flt(row.get("debit")) and not flt(row.get("credit")):
                flags.append(_("Zero Debit and Credit"))
        row["qfap_audit_flags"] = " | ".join(flags)
        row["qfap_audit_flag_count"] = len(flags)
    if not any(c.get("fieldname") == "qfap_audit_flags" for c in columns):
        columns.append({"label": _("Audit Flags"), "fieldname": "qfap_audit_flags", "fieldtype": "Data", "width": 260, "hidden": 1})


def _apply_analytical_filters(data, filters):
    search = (filters.get("qfap_audit_search") or "").strip().lower()
    min_raw, max_raw = filters.get("qfap_min_amount"), filters.get("qfap_max_amount")
    exceptions_only = bool(filters.get("qfap_exceptions_only"))
    active = bool(search or min_raw not in (None, "") or max_raw not in (None, "") or exceptions_only)
    if not active:
        return data, False
    minimum = flt(min_raw) if min_raw not in (None, "") else None
    maximum = flt(max_raw) if max_raw not in (None, "") else None
    filtered = []
    for row in data:
        if not _is_detail_row(row):
            continue
        amount = max(abs(flt(row.get("debit"))), abs(flt(row.get("credit"))))
        if minimum is not None and amount < minimum:
            continue
        if maximum is not None and amount > maximum:
            continue
        if exceptions_only and not row.get("qfap_audit_flag_count"):
            continue
        if search and search not in _search_text(row):
            continue
        filtered.append(row)
    return filtered, True


def _search_text(row):
    important = {"gl_entry", "account", "party_type", "party", "party_name", "voucher_type", "voucher_subtype", "voucher_no", "against", "against_voucher_type", "against_voucher", "bill_no", "remarks", "project", "cost_center"}
    return " ".join(str(v or "") for k, v in row.items() if k.startswith("qfap_") or k in important).lower()


def _apply_view(columns, view):
    compact = {"posting_date", "account", "debit", "credit", "balance", "voucher_type", "voucher_no", "project"}
    project_order = ["posting_date", "project", "cost_center", "account", "voucher_type", "voucher_no", "debit", "credit", "balance"]
    for column in columns:
        fieldname = column.get("fieldname")
        if view == "Compact":
            column["hidden"] = 0 if fieldname in compact else 1
        elif view == "Audit" and fieldname in {"qfap_audit_flags", "gl_entry", "remarks"}:
            column["hidden"] = 0
        elif view == "Project" and fieldname == "qfap_audit_flags":
            column["hidden"] = 0
    if view == "Project":
        order = {f: i for i, f in enumerate(project_order)}
        columns.sort(key=lambda c: order.get(c.get("fieldname"), 1000))


def _hide_empty_optional_columns(columns, data):
    protected = {"posting_date", "account", "debit", "credit", "balance", "voucher_type", "voucher_no"}
    for column in columns:
        fieldname = column.get("fieldname")
        if not fieldname or fieldname in protected or column.get("sticky"):
            continue
        if not any(row.get(fieldname) not in (None, "", 0) for row in data):
            column["hidden"] = 1


def _build_audit_summary(data, existing, dimensions):
    details = [r for r in data if _is_detail_row(r)]
    vouchers = {(r.get("voucher_type"), r.get("voucher_no")) for r in details if r.get("voucher_no")}
    accounts = {r.get("account") for r in details if r.get("account")}
    projects = {r.get("qfap_project_code") for r in details if r.get("qfap_project_code")}
    missing_project = sum(1 for r in details if not r.get("qfap_project_code"))
    missing_cc = sum(1 for r in details if not r.get("qfap_cost_center_code"))
    exceptions = sum(1 for r in details if r.get("qfap_audit_flag_count"))
    summary = list(existing or []) + [
        {"value": len(details), "label": _("GL Entries"), "datatype": "Int", "indicator": "blue"},
        {"value": len(vouchers), "label": _("Vouchers"), "datatype": "Int", "indicator": "blue"},
        {"value": len(accounts), "label": _("Accounts"), "datatype": "Int", "indicator": "blue"},
        {"value": len(projects), "label": _("Projects"), "datatype": "Int", "indicator": "blue"},
        {"value": exceptions, "label": _("Audit Exceptions"), "datatype": "Int", "indicator": "orange" if exceptions else "green"},
        {"value": missing_project, "label": _("Without Project"), "datatype": "Int", "indicator": "orange" if missing_project else "green"},
        {"value": missing_cc, "label": _("Without Cost Center"), "datatype": "Int", "indicator": "orange" if missing_cc else "green"},
    ]
    budget_fields = _budget_fields(dimensions)
    if budget_fields:
        missing_budget = sum(1 for r in details if not any(r.get(f) for f in budget_fields))
        summary.append({"value": missing_budget, "label": _("Without Budget Dimension"), "datatype": "Int", "indicator": "orange" if missing_budget else "green"})
    return summary


def _build_message(existing, subset_active):
    messages = [str(existing)] if existing else []
    messages.append(_("QFap audit flags are review indicators only. They do not change GL values or assert that a project, cost center, or budget dimension is mandatory."))
    if subset_active:
        messages.append(_("An analytical subset is active. Opening, Total, and Closing rows are omitted; displayed row balances retain their original GL context."))
    return "<br>".join(messages)


def _is_detail_row(row):
    return bool(row.get("posting_date") and row.get("gl_entry"))
