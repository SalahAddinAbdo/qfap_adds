from __future__ import annotations

import json

import frappe

WORKSPACE = "QFap Management Hub"
SIDEBAR = "QFap Adds"
DESKTOP_ICON = "QFap Adds"
OLD_WORKSPACES = ("Project Cycle Management",)
OLD_DESKTOP_ICONS = ("QFap Management Hub",)
APP_MODULE = "QFap Adds"

PROJECT_FORMS = [
    "Project", "Project Result", "Project Output", "Project Indicator",
    "Indicator Target Plan", "Project Workplan Activity", "Project Progress Update",
    "Project Risk", "Issue", "Project Change Request",
    "Project Compliance Deliverable", "Project Beneficiary Plan",
    "Project Closure", "Budget Line",
]
TASK_FORMS = ["Task", "Task Assignment Request"]
SIGNATURE_AND_PRINTING = [
    "Employee Signature", "Employee Signature Configuration",
    "QFAP Print Format Settings", "Print Format", "Letter Head",
]
MASTERS = ["Donor", "Donor Type", "Partner", "Governorate", "District"]
SETTINGS = [
    "Projects Settings", "Task Management Settings", "Notification", "Workflow",
    "Workflow State", "Workflow Action Master", "Email Template",
]
FEATURED_REPORTS = [
    "Project Portfolio Overview", "Project Progress", "Project Budget",
    "Indicator Performance", "Project Risks and Issues", "Beneficiary Reach",
    "Compliance Assurance", "Change Control", "Closure Readiness",
    "Project Data Quality", "Budget Versus Actual", "Employees Task Tracker",
]


def _exists(doctype, name):
    return bool(frappe.db.exists(doctype, name))


def _unique_existing(items, doctype="DocType"):
    result = []
    seen = set()
    for item in items:
        if item and item not in seen and _exists(doctype, item):
            seen.add(item)
            result.append(item)
    return result


def _app_doctypes():
    rows = frappe.get_all(
        "DocType",
        filters={"module": APP_MODULE, "istable": 0},
        fields=["name", "is_virtual"],
        order_by="name asc",
    )
    return [row.name for row in rows if not int(row.is_virtual or 0)]


def _app_reports():
    return frappe.get_all(
        "Report",
        filters={"module": APP_MODULE, "disabled": 0},
        pluck="name",
        order_by="name asc",
    ) or []


def _unassigned(all_items, groups):
    used = {item for group in groups for item in group}
    return [item for item in all_items if item not in used]


def _shortcut(label, link_to, link_type="DocType", color="Blue"):
    return {
        "label": label,
        "link_to": link_to,
        "type": link_type,
        "color": color,
        "doc_view": "List",
        "stats_filter": "[]",
    }


def _doc_card(label, items):
    return {
        "label": label,
        "links": [
            {"label": item, "link_to": item, "link_type": "DocType", "onboard": 0}
            for item in items
        ],
    }


def _report_card(label, items):
    return {
        "label": label,
        "links": [
            {"label": item, "link_to": item, "link_type": "Report", "onboard": 0}
            for item in items
        ],
    }


def _content(shortcuts, cards):
    blocks = [{
        "id": "qfap_hub_header",
        "type": "header",
        "data": {"text": '<span class="h4">QFap Management Hub</span>', "col": 12},
    }]
    for index, row in enumerate(shortcuts):
        blocks.append({
            "id": "qfap_shortcut_" + str(index),
            "type": "shortcut",
            "data": {"shortcut_name": row["label"], "col": 3},
        })
    blocks.append({"id": "qfap_cards_spacer", "type": "spacer", "data": {"col": 12}})
    for index, card in enumerate(cards):
        blocks.append({
            "id": "qfap_card_" + str(index),
            "type": "card",
            "data": {"card_name": card["label"], "col": 4},
        })
    return json.dumps(blocks, separators=(",", ":"))


def _workspace_links(cards):
    result = []
    for card in cards:
        result.append({
            "label": card["label"],
            "type": "Card Break",
            "link_count": len(card["links"]),
            "hidden": 0,
        })
        result.extend(card["links"])
    return result


def _remove_old_workspace():
    for old_name in OLD_WORKSPACES:
        if old_name != WORKSPACE and _exists("Workspace", old_name):
            frappe.delete_doc("Workspace", old_name, ignore_permissions=True, force=True)


def _save_workspace(data):
    if _exists("Workspace", WORKSPACE):
        doc = frappe.get_doc("Workspace", WORKSPACE)
        for key, value in data.items():
            if key not in ("doctype", "name") and doc.meta.has_field(key):
                doc.set(key, value)
        if doc.meta.has_field("type"):
            doc.type = "Workspace"
        doc.save(ignore_permissions=True)
        return

    meta = frappe.get_meta("Workspace")
    values = {
        key: value for key, value in data.items()
        if key in ("doctype", "name") or meta.has_field(key)
    }
    if meta.has_field("type"):
        values["type"] = "Workspace"
    frappe.get_doc(values).insert(ignore_permissions=True)


def _save_desktop_icon():
    """Upsert the Frappe 16 desktop tile using Workspace Sidebar link mode."""
    if not _exists("DocType", "Desktop Icon"):
        return

    for old_name in OLD_DESKTOP_ICONS:
        if old_name != DESKTOP_ICON and _exists("Desktop Icon", old_name):
            frappe.delete_doc(
                "Desktop Icon",
                old_name,
                ignore_permissions=True,
                force=True,
            )

    meta = frappe.get_meta("Desktop Icon")

    values = {
        "doctype": "Desktop Icon",
        "name": DESKTOP_ICON,
        "label": DESKTOP_ICON,
        "icon_type": "Link",
        "link_type": "Workspace Sidebar",
        "link_to": SIDEBAR,
        "sidebar": "",
        "app": "qfap_adds",
        "icon": "project",
        "logo_url": "/assets/qfap_adds/images/qfap_project_cycle.png",
        "hidden": 0,
        "standard": 1,
        "restrict_removal": 1,
        "idx": 50,
        "parent_icon": "",
    }

    values = {
        key: value
        for key, value in values.items()
        if key in ("doctype", "name") or meta.has_field(key)
    }

    if _exists("Desktop Icon", DESKTOP_ICON):
        doc = frappe.get_doc("Desktop Icon", DESKTOP_ICON)

        for key, value in values.items():
            if key not in ("doctype", "name"):
                doc.set(key, value)

        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc(values).insert(ignore_permissions=True)


def _refresh_desktop_layouts():
    if not _exists("DocType", "Desktop Layout"):
        return
    for name in frappe.get_all("Desktop Layout", pluck="name", limit_page_length=0):
        doc = frappe.get_doc("Desktop Layout", name)
        if DESKTOP_ICON not in str(doc.as_dict()):
            frappe.delete_doc("Desktop Layout", name, ignore_permissions=True, force=True)


def provision_project_navigation():
    app_doctypes = _app_doctypes()
    project_forms = _unique_existing(PROJECT_FORMS)
    task_forms = _unique_existing(TASK_FORMS)
    signature_printing = _unique_existing(SIGNATURE_AND_PRINTING)
    masters = _unique_existing(MASTERS)
    settings = _unique_existing(SETTINGS)
    classified = [project_forms, task_forms, signature_printing, masters, settings]
    other_app_forms = _unassigned(app_doctypes, classified)
    featured_reports = _unique_existing(FEATURED_REPORTS, "Report")
    all_reports = _unique_existing(featured_reports + _app_reports(), "Report")

    shortcuts = []
    for item in (
        "Project", "Task", "Project Progress Update", "Project Risk",
        "Project Change Request", "Employee Signature", "QFAP Print Format Settings",
    ):
        if _exists("DocType", item):
            shortcuts.append(_shortcut(item, item))
    for item in (
        "Project Portfolio Overview", "Budget Versus Actual", "Employees Task Tracker",
    ):
        if _exists("Report", item):
            shortcuts.append(_shortcut(item, item, "Report", "Green"))

    cards = []
    for label, items in (
        ("Project Cycle Management", project_forms),
        ("Task Management", task_forms),
        ("Signatures and Printing", signature_printing),
        ("Master Data", masters),
        ("Settings and Administration", settings),
        ("Other QFap Adds Forms", other_app_forms),
    ):
        if items:
            cards.append(_doc_card(label, items))
    if all_reports:
        cards.append(_report_card("Reports", all_reports))

    data = {
        "doctype": "Workspace",
        "name": WORKSPACE,
        "title": WORKSPACE,
        "label": WORKSPACE,
        "module": APP_MODULE,
        "type": "Workspace",
        "public": 1,
        "is_hidden": 0,
        "icon": "project",
        "content": _content(shortcuts, cards),
        "shortcuts": shortcuts,
        "links": _workspace_links(cards),
    }

    _remove_old_workspace()
    _save_workspace(data)
    _save_desktop_icon()
    _refresh_desktop_layouts()
    frappe.clear_cache()
