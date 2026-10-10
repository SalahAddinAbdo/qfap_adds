from pathlib import Path
import frappe
from frappe.modules import get_module_path


def sync():
    source_dir=Path(get_module_path("Accounts"))/"report"/"general_ledger"
    target_dir=Path(frappe.get_app_path("qfap_adds"))/"qfap_adds"/"report"/"enhanced_general_ledger"
    source_js=source_dir/"general_ledger.js"
    source_html=source_dir/"general_ledger.html"
    target_js=target_dir/"enhanced_general_ledger.js"
    target_html=target_dir/"enhanced_general_ledger.html"
    if not source_js.exists():
        frappe.throw(f"General Ledger JavaScript was not found: {source_js}")
    script=source_js.read_text(encoding="utf-8").replace('frappe.query_reports["General Ledger"]','frappe.query_reports["Enhanced General Ledger"]')
    script += ENHANCEMENT
    target_js.write_text(script,encoding="utf-8")
    if source_html.exists():
        target_html.write_text(source_html.read_text(encoding="utf-8"),encoding="utf-8")
    frappe.clear_cache()
    print(f"Synced {source_js} -> {target_js}")


ENHANCEMENT = r'\n\n// ---- QFap Adds enhancements; ERPNext filters and behaviors remain intact. ----\n(() => {\n  const config=frappe.query_reports["Enhanced General Ledger"];\n  if(!config || config.__pure_hands_enhanced) return;\n  config.__pure_hands_enhanced=true;\n  const original_formatter=config.formatter;\n  config.formatter=function(value,row,column,data,default_formatter){\n    let output=original_formatter ? original_formatter.call(this,value,row,column,data,default_formatter) : default_formatter(value,row,column,data);\n    if(data && column.fieldname==="project" && data.project_code){\n      const route=`/app/project/${encodeURIComponent(data.project_code)}`;\n      const title=frappe.utils.escape_html(data.project_name || data.project_code);\n      const label=frappe.utils.escape_html(String(value || data.project_code));\n      output=`<a href="${route}" title="${title}" class="ph-project-link">${label}</a>`;\n    }\n    return output;\n  };\n  const original_onload=config.onload;\n  config.onload=function(report){\n    if(original_onload) original_onload.call(this,report);\n    report.page.add_inner_button(__("Audit View"),()=>{\n      const values={include_dimensions:1,show_remarks:1,show_amount_in_company_currency:1};\n      Object.entries(values).forEach(([fieldname,value])=>{if(report.get_filter(fieldname)) report.set_filter_value(fieldname,value);});\n      report.refresh();\n    },__("View"));\n    report.page.add_inner_button(__("Standard View"),()=>{\n      ["show_remarks","show_amount_in_company_currency","add_values_in_transaction_currency"].forEach(fieldname=>{if(report.get_filter(fieldname)) report.set_filter_value(fieldname,0);});\n      report.refresh();\n    },__("View"));\n  };\n})();\n'
