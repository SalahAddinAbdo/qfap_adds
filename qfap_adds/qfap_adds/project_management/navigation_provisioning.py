from __future__ import annotations

import json
import frappe

WORKSPACE="Project Cycle Management"
FORMS=[
 "Project","Project Result","Project Indicator","Indicator Target Plan","Project Workplan Activity",
 "Project Progress Update","Project Risk","Issue","Project Change Request","Project Compliance Deliverable",
 "Project Beneficiary Plan","Project Closure","Budget Line","Task","Task Assignment Request",
]
MASTERS=["Donor","Donor Type","Partner","Governorate","District"]
SETTINGS=["Projects Settings","Task Management Settings"]
REPORTS=[
 "Project Portfolio Overview","Project Progress","Project Budget","Indicator Performance",
 "Project Risks and Issues","Beneficiary Reach","Compliance Assurance","Change Control",
 "Closure Readiness","Project Data Quality","Budget Versus Actual","Employees Task Tracker",
]


def _exists(kind,name):
    return bool(frappe.db.exists(kind,name))


def _shortcut(label,link_to,link_type="DocType",color="Blue"):
    return {"label":label,"link_to":link_to,"type":link_type,"color":color,"doc_view":"List","stats_filter":"[]"}


def _card(label,items):
    return {"label":label,"links":[{"label":x,"link_to":x,"link_type":"DocType","onboard":0} for x in items]}


def _report_card(label,items):
    return {"label":label,"links":[{"label":x,"link_to":x,"link_type":"Report","onboard":0} for x in items]}


def _content(shortcuts,cards):
    blocks=[{"id":"qfap_header","type":"header","data":{"text":"<span class=\\\"h4\\\">Project and Task Management</span>","col":12}}]
    for i,row in enumerate(shortcuts): blocks.append({"id":"qfap_shortcut_"+str(i),"type":"shortcut","data":{"shortcut_name":row["label"],"col":3}})
    blocks.append({"id":"qfap_links_header","type":"spacer","data":{"col":12}})
    for i,card in enumerate(cards): blocks.append({"id":"qfap_card_"+str(i),"type":"card","data":{"card_name":card["label"],"col":4}})
    return json.dumps(blocks,separators=(",",":"))


def _set_if(meta,data,field,value):
    if meta.has_field(field): data[field]=value


def provision_project_navigation():
    forms=[x for x in FORMS if _exists("DocType",x)]
    masters=[x for x in MASTERS if _exists("DocType",x)]
    settings=[x for x in SETTINGS if _exists("DocType",x)]
    reports=[x for x in REPORTS if _exists("Report",x)]
    shortcuts=[]
    for x in ["Project","Project Progress Update","Project Risk","Project Change Request","Task"]:
        if x in forms: shortcuts.append(_shortcut(x,x))
    for x in ["Project Portfolio Overview","Budget Versus Actual","Employees Task Tracker"]:
        if x in reports: shortcuts.append(_shortcut(x,x,"Report","Green"))
    cards=[_card("Project Cycle Forms",forms[:8]),_card("Assurance and Closure",forms[8:]),_card("Masters and Settings",masters+settings),_report_card("Reports",reports)]

    data={"doctype":"Workspace","name":WORKSPACE,"title":WORKSPACE,"label":WORKSPACE,"module":"QFap Adds","public":1,"is_hidden":0,"icon":"project","content":_content(shortcuts,cards),"shortcuts":shortcuts,"links":[]}
    for card in cards:
        for link in card["links"]:
            row=dict(link);row["type"]="Card Break" if not data["links"] or data["links"][-1].get("type")!="Card Break" else "Link"
        data["links"].append({"label":card["label"],"type":"Card Break","link_count":len(card["links"]),"hidden":0})
        data["links"].extend(card["links"])
    if _exists("Workspace",WORKSPACE):
        doc=frappe.get_doc("Workspace",WORKSPACE)
        for key,value in data.items():
            if key not in ("doctype","name") and doc.meta.has_field(key): doc.set(key,value)
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc(data).insert(ignore_permissions=True)

    # v16 main desktop icon. Metadata checks keep the routine forward-compatible.
    if frappe.db.exists("DocType","Desktop Icon"):
        meta=frappe.get_meta("Desktop Icon")
        values={"doctype":"Desktop Icon","name":WORKSPACE,"label":WORKSPACE,"app":"qfap_adds","icon":"project","icon_type":"Link","link_to":WORKSPACE,"link_type":"Workspace","logo_url":"/assets/qfap_adds/images/qfap_project_cycle.png","hidden":0,"standard":1,"restrict_removal":1,"idx":1}
        values={k:v for k,v in values.items() if k in ("doctype","name") or meta.has_field(k)}
        if frappe.db.exists("Desktop Icon",WORKSPACE):
            doc=frappe.get_doc("Desktop Icon",WORKSPACE)
            for k,v in values.items():
                if k not in ("doctype","name"): doc.set(k,v)
            doc.save(ignore_permissions=True)
        else: frappe.get_doc(values).insert(ignore_permissions=True)
    frappe.clear_cache()
