from __future__ import annotations
import json
import frappe

APP_MODULE="QFap Adds"
SIDEBAR="Q Org"
DESKTOP_ICON="Q Org"
WORKSPACES={
 "Q Management Hub": {"forms":["Project","Task","Project Progress Update","Project Risk","Project Change Request"],"reports":["Project Portfolio Overview","Budget Versus Actual","Employees Task Tracker"]},
 "Projects & Tasks": {"forms":["Project","Project Result","Project Indicator","Indicator Target Plan","Project Workplan Activity","Project Progress Update","Project Risk","Issue","Project Change Request","Project Compliance Deliverable","Project Beneficiary Plan","Project Closure","Budget Line","Task","Task Assignment Request","Projects Settings","Task Management Settings"],"reports":["Project Portfolio Overview","Project Progress","Project Budget","Indicator Performance","Project Risks and Issues","Beneficiary Reach","Compliance Assurance","Change Control","Closure Readiness","Project Data Quality","Budget Versus Actual","Employees Task Tracker"]},
 "Workflow & Documents": {"forms":["Workflow","Workflow State","Workflow Action Master","Employee Signature","Employee Signature Configuration","Print Settings","Print Format","Letter Head","Email Template","Notification"],"reports":[]},
 "Master Data": {"forms":["Donor","Donor Type","Partner","Governorate","District"],"reports":[]},
 "Reports & Analytics": {"forms":[],"reports":["Project Portfolio Overview","Project Progress","Project Budget","Indicator Performance","Project Risks and Issues","Beneficiary Reach","Compliance Assurance","Change Control","Closure Readiness","Project Data Quality","Budget Versus Actual","Employees Task Tracker"]},
}

def _exists(dt,name): return bool(frappe.db.exists(dt,name))
def _report_is_query(name):
    rt=frappe.db.get_value("Report",name,"report_type") or ""
    return 1 if rt in ("Script Report","Query Report") else 0
def _shortcut(name,typ):
    row={"label":name,"link_to":name,"type":typ,"color":"Green" if typ=="Report" else "Blue","doc_view":"List","stats_filter":"[]"}
    if typ=="Report": row["is_query_report"]=_report_is_query(name)
    return row
def _links(forms,reports):
    out=[]
    if forms:
        out.append({"label":"Forms","type":"Card Break","link_count":len(forms)})
        out += [{"label":x,"link_type":"DocType","link_to":x,"onboard":0,"type":"Link"} for x in forms]
    if reports:
        out.append({"label":"Reports","type":"Card Break","link_count":len(reports)})
        out += [{"label":x,"link_type":"Report","link_to":x,"onboard":0,"type":"Link","is_query_report":_report_is_query(x)} for x in reports]
    return out
def _content(shortcuts, cards, title):
    blocks=[{"id":"header","type":"header","data":{"text":f'<span class="h4">{title}</span>',"col":12}}]
    for i,s in enumerate(shortcuts): blocks.append({"id":f"s{i}","type":"shortcut","data":{"shortcut_name":s["label"],"col":3}})
    for i,c in enumerate(cards): blocks.append({"id":f"c{i}","type":"card","data":{"card_name":c,"col":4}})
    return json.dumps(blocks,separators=(",",":"))
def _save_workspace(name, forms, reports):
    forms=[x for x in forms if _exists("DocType",x)]
    reports=[x for x in reports if _exists("Report",x)]
    shortcuts=[_shortcut(x,"DocType") for x in forms[:5]]+[_shortcut(x,"Report") for x in reports[:3]]
    cards=[]
    if forms: cards.append("Forms")
    if reports: cards.append("Reports")
    values={"title":name,"label":name,"module":APP_MODULE,"type":"Workspace","public":1,"is_hidden":0,"icon":"project","content":_content(shortcuts,cards,name),"shortcuts":shortcuts,"links":_links(forms,reports)}
    if _exists("Workspace",name):
        doc=frappe.get_doc("Workspace",name)
        for k,v in values.items(): doc.set(k,v)
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc({"doctype":"Workspace","name":name,**values}).insert(ignore_permissions=True)
def _save_sidebar():
    definitions = [
        ("Q Management Hub", "Workspace", "Q Management Hub", "home"),
        ("Projects & Tasks", "Workspace", "Projects & Tasks", "project"),
        ("Workflow & Documents", "Workspace", "Workflow & Documents", "workflow"),
        ("Master Data", "Workspace", "Master Data", "data"),
        ("Reports & Analytics", "Workspace", "Reports & Analytics", "chart"),
        ("Projects", "DocType", "Project", "project"),
        ("Tasks", "DocType", "Task", "task"),
        ("Progress Updates", "DocType", "Project Progress Update", "calendar"),
        ("Project Risks", "DocType", "Project Risk", "warning"),
        ("Change Requests", "DocType", "Project Change Request", "change"),
        ("Compliance Deliverables", "DocType", "Project Compliance Deliverable", "milestone"),
        ("Portfolio Overview", "Report", "Project Portfolio Overview", "chart"),
        ("Budget Versus Actual", "Report", "Budget Versus Actual", "accounting"),
        ("Risks and Issues", "Report", "Project Risks and Issues", "warning"),
        ("Employee Task Tracker", "Report", "Employees Task Tracker", "users"),
        ("Project Settings", "DocType", "Projects Settings", "setting-gear"),
        ("Task Settings", "DocType", "Task Management Settings", "setting-gear"),
        ("Print Settings", "DocType", "Print Settings", "printer"),
    ]
    items = []
    for label, link_type, link_to, icon in definitions:
        if not _exists(link_type, link_to):
            continue
        row = {
            "label": label, "type": "Link", "link_type": link_type,
            "link_to": link_to, "icon": icon, "child": 0, "indent": 0,
            "collapsible": 1, "keep_closed": 0, "show_arrow": 0,
        }
        if link_type == "Report":
            row["is_query_report"] = _report_is_query(link_to)
        items.append(row)
    values = {
        "title": SIDEBAR, "module": APP_MODULE, "standard": 1,
        "app": "qfap_adds", "header_icon": "project", "items": items,
    }
    if _exists("Workspace Sidebar", SIDEBAR):
        doc = frappe.get_doc("Workspace Sidebar", SIDEBAR)
        for key, value in values.items():
            doc.set(key, value)
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc({"doctype": "Workspace Sidebar", "name": SIDEBAR, **values}).insert(ignore_permissions=True)

def _save_icon():
    values={"label":DESKTOP_ICON,"icon_type":"Link","link_type":"Workspace Sidebar","link_to":SIDEBAR,"sidebar":"","app":"qfap_adds","icon":"project","logo_url":"/assets/qfap_adds/images/qfap_project_cycle.png","hidden":0,"standard":1,"restrict_removal":1,"idx":50,"parent_icon":""}
    if _exists("Desktop Icon",DESKTOP_ICON):
        doc=frappe.get_doc("Desktop Icon",DESKTOP_ICON)
        for k,v in values.items():
            if doc.meta.has_field(k): doc.set(k,v)
        doc.save(ignore_permissions=True)
    else: frappe.get_doc({"doctype":"Desktop Icon","name":DESKTOP_ICON,**{k:v for k,v in values.items() if frappe.get_meta("Desktop Icon").has_field(k)}}).insert(ignore_permissions=True)
def _integrate_standard_workspace(name, links):
    """Add a Q Org card to a standard Workspace using supported link types only.

    Workspace Link rows in Frappe 16 accept DocType, Page, or Report. Direct
    Workspace-to-Workspace links belong in Workspace Sidebar, not Workspace Link.
    """
    if not _exists("Workspace", name):
        return

    supported_types = {"DocType", "Page", "Report"}
    valid_links = []
    for label, link_type, link_to in links:
        if link_type not in supported_types or not _exists(link_type, link_to):
            continue
        valid_links.append((label, link_type, link_to))

    doc = frappe.get_doc("Workspace", name)
    managed_labels = {label for label, _, _ in valid_links}
    current = []
    skip_qorg_block = False

    for row in doc.links or []:
        if row.type == "Card Break":
            skip_qorg_block = row.label == "Q Org"
            if skip_qorg_block:
                continue
        elif skip_qorg_block and row.type == "Link":
            continue
        else:
            skip_qorg_block = False

        if row.type == "Link" and row.label in managed_labels:
            continue
        current.append(row.as_dict())

    if valid_links:
        current.append({
            "label": "Q Org",
            "type": "Card Break",
            "link_count": len(valid_links),
        })
        for label, link_type, link_to in valid_links:
            row = {
                "label": label,
                "type": "Link",
                "link_type": link_type,
                "link_to": link_to,
                "onboard": 0,
            }
            if link_type == "Report":
                row["is_query_report"] = _report_is_query(link_to)
            current.append(row)

    doc.set("links", current)
    doc.save(ignore_permissions=True)


def provision_q_org_navigation():
    for n,c in WORKSPACES.items(): _save_workspace(n,c["forms"],c["reports"])
    _save_sidebar(); _save_icon()
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
