from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.general_ledger import general_ledger


def execute(filters=None):
    """Run ERPNext General Ledger, then add non-posting audit presentation."""
    filters = frappe._dict(filters or {})
    _validate_analytical_filters(filters)
    dimensions = _get_active_dimensions()
    _validate_dimension_dependencies(filters, dimensions)

    dimension_field = _get_dimension_category_field(filters.get("categorize_by"))
    if dimension_field:
        columns, data, message, chart, report_summary, skip_total_row = _execute_dimension_categorization(
            filters, dimensions, dimension_field
        )
    else:
        result = list(general_ledger.execute(filters) or ([], []))
        while len(result) < 6:
            result.append(None)
        columns, data, message, chart, report_summary, skip_total_row = result[:6]
        columns, data = columns or [], data or []
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
        "qfap_ledger_search", "qfap_min_amount", "qfap_max_amount", "qfap_exceptions_only"
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
    search = (filters.get("qfap_ledger_search") or "").strip().lower()
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
    focus_field = ""
    if view == "Project":
        focus_field = "project"
    elif str(view).startswith("Dimension::"):
        focus_field = str(view).split("::", 1)[1]
    focus_order = ["posting_date"]
    if focus_field:
        focus_order.append(focus_field)
    for fieldname in ["project", "cost_center", "account", "voucher_type", "voucher_no", "debit", "credit", "balance"]:
        if fieldname not in focus_order:
            focus_order.append(fieldname)
    for column in columns:
        fieldname = column.get("fieldname")
        if view == "Compact":
            column["hidden"] = 0 if fieldname in compact else 1
        elif view == "Audit" and fieldname in {"qfap_audit_flags", "gl_entry", "remarks"}:
            column["hidden"] = 0
        elif focus_field and fieldname == "qfap_audit_flags":
            column["hidden"] = 0
    if focus_field:
        order = {fieldname: index for index, fieldname in enumerate(focus_order)}
        columns.sort(key=lambda column: order.get(column.get("fieldname"), 1000))

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



def _as_list(value):
    if not value:
        return []
    if isinstance(value, str):
        try:
            value = frappe.parse_json(value)
        except Exception:
            value = [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, (list, tuple, set)):
        value = [value]
    output = []
    for item in value:
        if isinstance(item, dict):
            item = item.get("value")
        if item and str(item) not in output:
            output.append(str(item))
    return output


def _get_dimension_category_field(categorize_by):
    prefix = "Categorize by Dimension::"
    value = str(categorize_by or "")
    return value[len(prefix):] if value.startswith(prefix) else ""


def _dimension_map(dimensions):
    result = {
        "project": frappe._dict(
            fieldname="project",
            label=_("Project"),
            document_type="Project",
        ),
        "cost_center": frappe._dict(
            fieldname="cost_center",
            label=_("Cost Center"),
            document_type="Cost Center",
        ),
    }
    for dimension in dimensions:
        result[dimension.fieldname] = dimension
    return result


def _validate_dimension_dependencies(filters, dimensions):
    projects = _as_list(filters.get("project"))
    for dimension in dimensions:
        if dimension.document_type != "Budget Line":
            continue
        selected = _as_list(filters.get(dimension.fieldname))
        if not selected:
            continue
        if not projects:
            frappe.throw(_("Select a Project before filtering by Budget Line."))
        invalid = frappe.get_list(
            "Budget Line",
            filters={"name": ["in", selected], "project": ["not in", projects]},
            pluck="name",
            limit_page_length=0,
        )
        if invalid:
            frappe.throw(_("The selected Budget Line does not belong to the selected Project."))


def _execute_dimension_categorization(filters, dimensions, fieldname):
    dimension = _dimension_map(dimensions).get(fieldname)
    if not dimension:
        frappe.throw(_("The selected accounting dimension is not enabled."))

    values = _get_dimension_group_values(filters, dimension)
    all_columns, grouped_data = [], []
    report_summary = []
    skip_total_row = 1

    for value in values:
        local_filters = frappe._dict(filters.copy())
        local_filters["categorize_by"] = ""
        local_filters["include_dimensions"] = 1
        local_filters[fieldname] = [value]
        for key in list(local_filters.keys()):
            if str(key).startswith("qfap_"):
                local_filters.pop(key, None)

        result = list(general_ledger.execute(local_filters) or ([], []))
        while len(result) < 6:
            result.append(None)
        columns, rows = result[0] or [], result[1] or []
        detail_rows = [row for row in rows if _is_detail_row(row)]
        meaningful_totals = any(
            flt(row.get("debit")) or flt(row.get("credit")) or flt(row.get("balance"))
            for row in rows
            if not _is_detail_row(row)
        )
        if not detail_rows and not meaningful_totals:
            continue
        if not all_columns:
            all_columns = columns
        title = _get_dimension_value_title(dimension.document_type, value)
        grouped_data.append({
            "account": f"{dimension.label or fieldname}: {value}" + (f" - {title}" if title and title != value else ""),
            fieldname: value,
            "qfap_dimension_group_header": 1,
        })
        grouped_data.extend(rows)
        grouped_data.append({})

    grand_total_rows = _get_grand_total_rows(filters)
    if grand_total_rows:
        grouped_data.append({})
        grouped_data.append(
            {
                "account": _("Grand Total for All Groups"),
                "qfap_dimension_group_header": 1,
                "qfap_grand_total_header": 1,
            }
        )
        grouped_data.extend(grand_total_rows)

    message = _(
        "Dimension categorization uses ERPNext General Ledger separately for each dimension value. "
        "The Grand Total section is taken directly from the final Total and Closing rows returned "
        "by the standard accounting engine for the complete filtered ledger scope."
    )
    return all_columns, grouped_data, message, None, report_summary, skip_total_row


def _get_grand_total_rows(filters):
    total_filters = frappe._dict(filters.copy())
    total_filters["categorize_by"] = ""
    for key in list(total_filters.keys()):
        if str(key).startswith("qfap_"):
            total_filters.pop(key, None)

    result = list(general_ledger.execute(total_filters) or ([], []))
    rows = result[1] if len(result) > 1 and result[1] else []

    # ERPNext General Ledger appends the overall Total and Closing rows at the end.
    # Select the last two labelled, non-detail rows rather than relying on translated text.
    labelled_rows = []
    for row in reversed(rows):
        if _is_detail_row(row):
            continue
        if not row.get("account"):
            continue
        labelled_rows.insert(0, row)
        if len(labelled_rows) == 2:
            break
    return labelled_rows

def _get_dimension_group_values(filters, dimension):
    selected = _as_list(filters.get(dimension.fieldname))
    meta = frappe.get_meta(dimension.document_type)
    master_filters = {}
    projects = _as_list(filters.get("project"))
    project_field = _find_project_field(meta)
    if projects and project_field:
        master_filters[project_field] = ["in", projects]

    if selected:
        if meta.is_tree:
            expanded = []
            for name in selected:
                node = frappe.db.get_value(dimension.document_type, name, ["lft", "rgt"], as_dict=True)
                if node:
                    descendants = frappe.get_list(
                        dimension.document_type,
                        filters={**master_filters, "lft": [">=", node.lft], "rgt": ["<=", node.rgt]},
                        pluck="name",
                        order_by="lft asc",
                        limit_page_length=0,
                    )
                    expanded.extend(descendants)
            return list(dict.fromkeys(expanded))
        return selected

    gl_filters = {"company": filters.get("company"), "posting_date": ["<=", filters.get("to_date")]}
    if projects:
        gl_filters["project"] = ["in", projects]
    rows = frappe.get_list(
        "GL Entry",
        filters=gl_filters,
        fields=[dimension.fieldname],
        group_by=dimension.fieldname,
        limit_page_length=0,
    )
    values = [row.get(dimension.fieldname) for row in rows if row.get(dimension.fieldname)]
    if meta.is_tree and values:
        ordering = frappe.get_list(
            dimension.document_type,
            filters={**master_filters, "name": ["in", values]},
            fields=["name", "lft"],
            order_by="lft asc",
            limit_page_length=0,
        )
        return [row.name for row in ordering]
    return sorted(set(values))


def _find_project_field(meta):
    for field in meta.fields:
        if field.fieldtype == "Link" and field.options == "Project":
            if field.fieldname == "project":
                return field.fieldname
    for field in meta.fields:
        if field.fieldtype == "Link" and field.options == "Project":
            return field.fieldname
    return ""


def _get_dimension_value_title(document_type, name):
    meta = frappe.get_meta(document_type)
    if document_type == "Budget Line":
        row = frappe.db.get_value(
            document_type,
            name,
            ["budget_line", "name1", "project"],
            as_dict=True,
        )
        if not row:
            return name
        label = " - ".join(
            [value for value in [row.get("budget_line"), row.get("name1")] if value]
        ) or name
        if row.get("project"):
            label += " | " + _("Project") + ": " + str(row.get("project"))
        return label
    title_field = meta.title_field if meta.title_field and meta.has_field(meta.title_field) else ""
    return frappe.db.get_value(document_type, name, title_field) if title_field else name


@frappe.whitelist()
def get_qfap_dimension_config():
    result = []
    for dimension in _get_active_dimensions():
        meta = frappe.get_meta(dimension.document_type)
        result.append({
            "fieldname": dimension.fieldname,
            "label": dimension.label or dimension.fieldname.replace("_", " ").title(),
            "document_type": dimension.document_type,
            "is_tree": bool(meta.is_tree),
            "parent_field": meta.nsm_parent_field or "",
            "project_field": _find_project_field(meta),
            "is_budget_line": dimension.document_type == "Budget Line",
        })
    return result


@frappe.whitelist()
def get_budget_line_options(txt="", projects=None, limit=50):
    project_list = _as_list(projects)
    if not project_list:
        return []
    if not frappe.has_permission("Budget Line", "read"):
        frappe.throw(_("You do not have permission to read Budget Line."), frappe.PermissionError)
    filters = {"project": ["in", project_list]}
    fields = ["name", "project", "budget_line", "name1", "status", "is_group", "line_cost", "currency", "lft"]
    or_filters = {}
    if txt:
        like = "%" + txt + "%"
        or_filters = {"name": ["like", like], "budget_line": ["like", like], "name1": ["like", like]}
    rows = frappe.get_list(
        "Budget Line",
        filters=filters,
        or_filters=or_filters,
        fields=fields,
        order_by="project asc, lft asc",
        limit_page_length=min(int(limit or 50), 100),
    )
    output = []
    for row in rows:
        label = " - ".join([part for part in [row.budget_line, row.name1] if part]) or row.name
        description = [_('Project') + ": " + str(row.project)]
        if row.is_group:
            description.append(_("Group node; selecting it includes descendants"))
        if row.status:
            description.append(_("Status") + ": " + str(row.status))
        if row.line_cost not in (None, ""):
            description.append(_("Budget") + ": " + str(row.line_cost) + (" " + str(row.currency) if row.currency else ""))
        output.append({"value": row.name, "label": label, "description": " | ".join(description)})
    return output
