from __future__ import annotations

import json

import frappe

APP_MODULE = "QFap Adds"
SIDEBAR = "Q Org"
DESKTOP_ICON = "Q Org"

WORKSPACE_GROUPS = {
    "Q Management Hub": [
        ("Workspaces", "Workspace", [
            "Projects & Tasks", "Workflow & Documents", "Master Data", "Reports & Analytics",
        ]),
        ("Priority Documents", "DocType", [
            "Project", "Task", "Project Progress Update", "Project Risk", "Project Change Request",
        ]),
        ("Priority Reports", "Report", [
            "Project Portfolio Overview", "Budget Versus Actual", "Employees Task Tracker",
        ]),
    ],
    "Projects & Tasks": [
        ("Project Setup & Planning", "DocType", [
            "Project", "Project Result", "Project Indicator", "Indicator Target Plan",
            "Project Workplan Activity", "Budget Line",
        ]),
        ("Monitoring & Control", "DocType", [
            "Project Progress Update", "Project Risk", "Issue", "Project Change Request",
            "Project Compliance Deliverable", "Project Beneficiary Plan", "Project Closure",
        ]),
        ("Task Management", "DocType", [
            "Task", "Task Assignment Request",
        ]),
        ("Performance Reports", "Report", [
            "Project Portfolio Overview", "Project Progress", "Indicator Performance",
            "Beneficiary Reach", "Project Data Quality",
        ]),
        ("Control & Assurance Reports", "Report", [
            "Project Risks and Issues", "Compliance Assurance", "Change Control",
            "Closure Readiness",
        ]),
        ("Financial & Task Reports", "Report", [
            "Project Budget", "Budget Versus Actual", "Employees Task Tracker",
        ]),
        ("Project & Task Settings", "DocType", [
            "Projects Settings", "Task Management Settings",
        ]),
    ],
    "Workflow & Documents": [
        ("Workflow Configuration", "DocType", [
            "Workflow", "Workflow State", "Workflow Action Master",
        ]),
        ("Signatures", "DocType", [
            "Employee Signature", "Employee Signature Configuration",
        ]),
        ("Printing", "DocType", [
            "Print Settings", "Print Format", "Letter Head",
        ]),
        ("Templates & Notifications", "DocType", [
            "Email Template", "Notification",
        ]),
    ],
    "Master Data": [
        ("Organizations", "DocType", [
            "Donor", "Donor Type", "Partner",
        ]),
        ("Geographic Data", "DocType", [
            "Governorate", "District",
        ]),
    ],
    "Reports & Analytics": [
        ("Executive & Performance", "Report", [
            "Project Portfolio Overview", "Project Progress", "Indicator Performance",
            "Project Data Quality",
        ]),
        ("Risk, Compliance & Change", "Report", [
            "Project Risks and Issues", "Compliance Assurance", "Change Control",
            "Closure Readiness",
        ]),
        ("Financial & Beneficiaries", "Report", [
            "Project Budget", "Budget Versus Actual", "Beneficiary Reach",
        ]),
        ("Task Reports", "Report", [
            "Employees Task Tracker",
        ]),
    ],
}

SIDEBAR_DEFINITIONS = [
    ("Q Management Hub", "Workspace", "Q Management Hub", "home"),
    ("Projects & Tasks", "Workspace", "Projects & Tasks", "folder-normal"),
    ("Workflow & Documents", "Workspace", "Workflow & Documents", "workflow"),
    ("Master Data", "Workspace", "Master Data", "folder-normal"),
    ("Reports & Analytics", "Workspace", "Reports & Analytics", "chart"),
    ("Projects", "DocType", "Project", "folder-normal"),
    ("Tasks", "DocType", "Task", "folder-normal"),
    ("Progress Updates", "DocType", "Project Progress Update", "calendar"),
    ("Project Risks", "DocType", "Project Risk", "folder-normal"),
    ("Change Requests", "DocType", "Project Change Request", "change"),
    ("Compliance Deliverables", "DocType", "Project Compliance Deliverable", "folder-normal"),
    ("Portfolio Overview", "Report", "Project Portfolio Overview", "chart"),
    ("Budget Versus Actual", "Report", "Budget Versus Actual", "accounting"),
    ("Risks and Issues", "Report", "Project Risks and Issues", "chart"),
    ("Employee Task Tracker", "Report", "Employees Task Tracker", "users"),
    ("Project Settings", "DocType", "Projects Settings", "setting-gear"),
    ("Task Settings", "DocType", "Task Management Settings", "setting-gear"),
    ("Print Settings", "DocType", "Print Settings", "printer"),
]


def _exists(doctype, name):
    return bool(frappe.db.exists(doctype, name))


def _report_is_query(name):
    report_type = frappe.db.get_value("Report", name, "report_type") or ""
    return 1 if report_type in ("Script Report", "Query Report") else 0


def _valid_items(link_type, items):
    return [item for item in items if _exists(link_type, item)]


def _shortcut(name, link_type, color="Blue"):
    row = {
        "label": name,
        "link_to": name,
        "type": link_type,
        "color": color,
        "doc_view": "List",
        "stats_filter": "[]",
    }
    if link_type == "Report":
        row["is_query_report"] = _report_is_query(name)
    return row


def _workspace_link_rows(groups):
    rows = []
    for label, link_type, items in groups:
        valid = _valid_items(link_type, items)
        if not valid:
            continue
        rows.append({"label": label, "type": "Card Break", "link_count": len(valid)})
        for item in valid:
            row = {
                "label": item,
                "type": "Link",
                "link_type": link_type,
                "link_to": item,
                "onboard": 0,
            }
            if link_type == "Report":
                row["is_query_report"] = _report_is_query(item)
            rows.append(row)
    return rows


def _content(title, shortcuts, card_labels):
    blocks = [{
        "id": "qorg_header",
        "type": "header",
        "data": {"text": f'<span class="h4">{title}</span>', "col": 12},
    }]
    for index, row in enumerate(shortcuts):
        blocks.append({
            "id": f"qorg_shortcut_{index}",
            "type": "shortcut",
            "data": {"shortcut_name": row["label"], "col": 3},
        })
    if card_labels:
        blocks.append({"id": "qorg_spacer", "type": "spacer", "data": {"col": 12}})
    for index, label in enumerate(card_labels):
        blocks.append({
            "id": f"qorg_card_{index}",
            "type": "card",
            "data": {"card_name": label, "col": 4},
        })
    return json.dumps(blocks, separators=(",", ":"))


def _save_workspace(name, groups):
    normalized = []
    for label, link_type, items in groups:
        valid = _valid_items(link_type, items)
        if valid:
            normalized.append((label, link_type, valid))

    shortcuts = []
    for _, link_type, items in normalized:
        for item in items:
            shortcuts.append(_shortcut(item, link_type, "Green" if link_type == "Report" else "Blue"))
            if len(shortcuts) == 8:
                break
        if len(shortcuts) == 8:
            break

    card_labels = [label for label, _, _ in normalized]
    values = {
        "title": name,
        "label": name,
        "module": APP_MODULE,
        "type": "Workspace",
        "public": 1,
        "is_hidden": 0,
        "icon": "project",
        "content": _content(name, shortcuts, card_labels),
        "shortcuts": shortcuts,
        "links": _workspace_link_rows(normalized),
    }

    if _exists("Workspace", name):
        doc = frappe.get_doc("Workspace", name)
        for key, value in values.items():
            doc.set(key, value)
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc({"doctype": "Workspace", "name": name, **values}).insert(ignore_permissions=True)


def _save_sidebar():
    items = []
    for label, link_type, link_to, icon in SIDEBAR_DEFINITIONS:
        if not _exists(link_type, link_to):
            continue
        row = {
            "label": label,
            "type": "Link",
            "link_type": link_type,
            "link_to": link_to,
            "icon": icon,
            "child": 0,
            "indent": 0,
            "collapsible": 1,
            "keep_closed": 0,
            "show_arrow": 0,
        }
        if link_type == "Report":
            row["is_query_report"] = _report_is_query(link_to)
        items.append(row)

    values = {
        "title": SIDEBAR,
        "module": APP_MODULE,
        "standard": 1,
        "app": "qfap_adds",
        "header_icon": "project",
        "items": items,
    }
    if _exists("Workspace Sidebar", SIDEBAR):
        doc = frappe.get_doc("Workspace Sidebar", SIDEBAR)
        for key, value in values.items():
            doc.set(key, value)
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc({"doctype": "Workspace Sidebar", "name": SIDEBAR, **values}).insert(ignore_permissions=True)


def _save_icon():
    values = {
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
    meta = frappe.get_meta("Desktop Icon")
    if _exists("Desktop Icon", DESKTOP_ICON):
        doc = frappe.get_doc("Desktop Icon", DESKTOP_ICON)
        for key, value in values.items():
            if meta.has_field(key):
                doc.set(key, value)
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc({
            "doctype": "Desktop Icon",
            "name": DESKTOP_ICON,
            **{key: value for key, value in values.items() if meta.has_field(key)},
        }).insert(ignore_permissions=True)


def _integrate_standard_workspace(name, links):
    """Add a visible Q Org card to a standard Frappe 16 Workspace.

    Workspace Link child rows define card membership, while Workspace.content
    controls which cards are rendered. Both structures must be updated.
    """
    if not _exists("Workspace", name):
        return

    valid = [
        (label, link_type, target)
        for label, link_type, target in links
        if link_type in {"DocType", "Page", "Report"} and _exists(link_type, target)
    ]
    doc = frappe.get_doc("Workspace", name)

    # Remove the previously managed Q Org card and its links, then rebuild it.
    rebuilt_links = []
    skipping_qorg_links = False
    for row in doc.links or []:
        if row.type == "Card Break":
            skipping_qorg_links = row.label == "Q Org"
            if skipping_qorg_links:
                continue
        elif skipping_qorg_links and row.type == "Link":
            continue
        else:
            skipping_qorg_links = False
        rebuilt_links.append(row.as_dict())

    if valid:
        rebuilt_links.append({
            "label": "Q Org",
            "type": "Card Break",
            "link_count": len(valid),
        })
        for label, link_type, target in valid:
            row = {
                "label": label,
                "type": "Link",
                "link_type": link_type,
                "link_to": target,
                "onboard": 0,
            }
            if link_type == "Report":
                row["is_query_report"] = _report_is_query(target)
            rebuilt_links.append(row)

    # Workspace.content is the visual layout. A Link Card does not render merely
    # because its Card Break exists in doc.links.
    try:
        content = json.loads(doc.content or "[]")
    except Exception:
        content = []
    if not isinstance(content, list):
        content = []

    cleaned_content = []
    for block in content:
        data = block.get("data") or {}
        is_qorg_card = block.get("type") == "card" and data.get("card_name") == "Q Org"
        is_qorg_spacer = block.get("id") == "qorg_standard_workspace_spacer"
        if not is_qorg_card and not is_qorg_spacer:
            cleaned_content.append(block)

    if valid:
        cleaned_content.append({
            "id": "qorg_standard_workspace_spacer",
            "type": "spacer",
            "data": {"col": 12},
        })
        cleaned_content.append({
            "id": "qorg_standard_workspace_card",
            "type": "card",
            "data": {"card_name": "Q Org", "col": 4},
        })

    doc.set("links", rebuilt_links)
    doc.content = json.dumps(cleaned_content, separators=(",", ":"))
    doc.save(ignore_permissions=True)


def provision_q_org_navigation():
    for name, groups in WORKSPACE_GROUPS.items():
        _save_workspace(name, groups)
    _save_sidebar()
    _save_icon()
    _integrate_standard_workspace("Projects", [
        ("Project Results", "DocType", "Project Result"),
        ("Project Progress", "Report", "Project Progress"),
        ("Budget Versus Actual", "Report", "Budget Versus Actual"),
    ])
    _integrate_standard_workspace("Accounts", [
        ("Budget Lines", "DocType", "Budget Line"),
        ("Budget Versus Actual", "Report", "Budget Versus Actual"),
    ])
    frappe.clear_cache()
