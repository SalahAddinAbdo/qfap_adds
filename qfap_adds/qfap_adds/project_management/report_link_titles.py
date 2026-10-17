from __future__ import annotations

import frappe


def _has_report_value(value):
    """Return True when a report cell contains meaningful display data.

    Numeric zero and boolean False are valid values and keep their columns.
    Only None, blank text and empty containers are considered empty.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _add_link_titles(columns, rows):
    link_columns = []
    for column in columns:
        if not isinstance(column, dict) or column.get("fieldtype") != "Link":
            continue
        fieldname = column.get("fieldname")
        linked_doctype = column.get("options")
        if not fieldname or not linked_doctype or not frappe.db.exists("DocType", linked_doctype):
            continue
        meta = frappe.get_meta(linked_doctype)
        title_field = meta.title_field
        if not meta.show_title_field_in_link or not title_field or not meta.has_field(title_field):
            continue
        link_columns.append((fieldname, linked_doctype, title_field))

    for fieldname, linked_doctype, title_field in link_columns:
        names = []
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = row.get(fieldname)
            if name and name not in seen:
                seen.add(name)
                names.append(name)
        if not names:
            continue
        title_rows = frappe.get_all(
            linked_doctype,
            filters={"name": ["in", names]},
            fields=["name", title_field],
            limit_page_length=0,
        )
        title_map = {item.name: item.get(title_field) for item in title_rows}
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = row.get(fieldname)
            title = title_map.get(name)
            if title and str(title) != str(name):
                row[fieldname + "__title"] = title


def finalize_report_result(result):
    """Apply report-wide presentation rules in one deterministic pass.

    1. Add configured Link titles without altering Link values.
    2. Remove a displayed column only when every returned row is empty.
    3. Reapply native Frappe sticky to the first two remaining columns.
    """
    if not result:
        return result
    values = list(result) if isinstance(result, (tuple, list)) else [result]
    if len(values) < 2:
        return result
    columns = values[0] or []
    rows = values[1] or []
    if not isinstance(columns, list) or not isinstance(rows, list):
        return result

    _add_link_titles(columns, rows)

    visible_columns = []
    for column in columns:
        if not isinstance(column, dict):
            visible_columns.append(column)
            continue
        fieldname = column.get("fieldname")
        if not fieldname:
            visible_columns.append(column)
            continue
        if any(isinstance(row, dict) and _has_report_value(row.get(fieldname)) for row in rows):
            visible_columns.append(column)

    for index, column in enumerate(visible_columns):
        if isinstance(column, dict):
            column["sticky"] = bool(index < 2)

    values[0] = visible_columns
    values[1] = rows
    return tuple(values)


# Backward-compatible alias for any external import from v2.8.4.
def add_link_titles(result):
    return finalize_report_result(result)
