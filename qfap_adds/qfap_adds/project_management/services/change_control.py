from __future__ import annotations
import json
import frappe
from frappe import _
from qfap_adds.qfap_adds.project_management.settings import get_project_cycle_settings

ALLOWED_FIELDS={
 "Project":{"expected_start_date","expected_end_date","custom_project_health"},
 "Project Result":{"result_statement","weight","status"},
 "Project Indicator":{"life_of_project_target","reporting_frequency","status"},
 "Indicator Target Plan":{"target_value","period_start_date","period_end_date"},
 "Project Workplan Activity":{"planned_start_date","planned_end_date","planned_quantity","weight","status"},
 "Project Compliance Deliverable":{"due_date","responsible_employee","status"},
}

def apply_change_request(doc):
    settings=get_project_cycle_settings()
    if not settings.enable_automatic_change_application: frappe.throw(_("Automatic Change Application is disabled in Projects Settings."))
    if doc.status != "Approved": frappe.throw(_("Only an Approved Change Request can be applied."))
    if doc.change_applied: return
    configured={(row.target_doctype,row.field_name) for row in settings.project_change_allowed_fields if row.get("enabled")}
    changed=[]
    for row in doc.get("affected_items") or []:
        doctype=row.get("reference_doctype"); name=row.get("reference_name"); field=row.get("field_name")
        if not doctype or not name or not field: continue
        if field not in ALLOWED_FIELDS.get(doctype,set()) or (configured and (doctype,field) not in configured): frappe.throw(_("Field {0}.{1} is not allowed for automated change application.").format(doctype,field))
        if not frappe.db.exists(doctype,name): frappe.throw(_("Affected record {0} {1} does not exist.").format(doctype,name))
        old=frappe.db.get_value(doctype,name,field)
        new=row.get("proposed_value")
        frappe.db.set_value(doctype,name,field,new,update_modified=True)
        for fn,val in (("current_value",old),("applied_value",new),("applied",1)):
            if row.meta.has_field(fn): row.db_set(fn,val,update_modified=False)
        changed.append({"doctype":doctype,"name":name,"field":field,"old":old,"new":new})
    if not changed: frappe.throw(_("No valid affected items were available to apply."))
    doc.db_set("change_applied",1,update_modified=False)
    if doc.meta.has_field("implementation_notes"): doc.db_set("implementation_notes",json.dumps(changed,default=str),update_modified=False)
