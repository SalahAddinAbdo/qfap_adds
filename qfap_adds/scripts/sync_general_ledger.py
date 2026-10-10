from __future__ import annotations

from pathlib import Path

import frappe
from frappe.modules import get_module_path


ENHANCEMENT = """

// ---- QFap Adds v1.1 enhancements; ERPNext filters and behavior remain intact. ----
(() => {
  const reportName = "Enhanced General Ledger";
  const config = frappe.query_reports[reportName];
  if (!config || config.__qfap_adds_v11_enhanced) return;
  config.__qfap_adds_v11_enhanced = true;

  const filters = [
    {fieldname:"qfap_view",label:__("QFap View"),fieldtype:"Select",options:["Standard","Compact","Audit","Project"].join("\\n"),default:"Standard",on_change:()=>frappe.query_report.refresh()},
    {fieldname:"qfap_audit_search",label:__("Audit Search"),fieldtype:"Data",description:__("Search accounts, vouchers, parties, projects, dimensions, invoice numbers, and remarks")},
    {fieldname:"qfap_min_amount",label:__("Minimum Amount"),fieldtype:"Currency"},
    {fieldname:"qfap_max_amount",label:__("Maximum Amount"),fieldtype:"Currency"},
    {fieldname:"qfap_exceptions_only",label:__("Audit Exceptions Only"),fieldtype:"Check",default:0},
    {fieldname:"qfap_hide_empty_columns",label:__("Hide Empty Columns"),fieldtype:"Check",default:1},
  ];
  const existing = new Set((config.filters || []).map(f=>f.fieldname));
  filters.forEach(f=>{if(!existing.has(f.fieldname)) config.filters.push(f);});

  const originalFormatter = config.formatter;
  config.formatter = function(value,row,column,data,defaultFormatter){
    let output = originalFormatter ? originalFormatter.call(this,value,row,column,data,defaultFormatter) : defaultFormatter(value,row,column,data);
    if(data && column.qfap_link_doctype && column.qfap_code_field){
      const code=data[column.qfap_code_field];
      if(code){
        const title=data[column.qfap_title_field] || code;
        const route=`/app/${frappe.router.slug(column.qfap_link_doctype)}/${encodeURIComponent(code)}`;
        output=`<a href="${route}" title="${frappe.utils.escape_html(String(title))}" class="qfap-dimension-link">${frappe.utils.escape_html(String(value || code))}</a>`;
      }
    }
    if(data && column.fieldname==="qfap_audit_flags" && value){
      output=`<span class="indicator-pill orange" title="${frappe.utils.escape_html(String(value))}">${frappe.utils.escape_html(String(value))}</span>`;
    }
    return output;
  };

  const originalOnload=config.onload;
  config.onload=function(report){
    if(originalOnload) originalOnload.call(this,report);
    report.page.add_inner_button(__("Standard View"),()=>setView(report,"Standard"),__("QFap Views"));
    report.page.add_inner_button(__("Compact View"),()=>setView(report,"Compact"),__("QFap Views"));
    report.page.add_inner_button(__("Audit View"),()=>setView(report,"Audit"),__("QFap Views"));
    report.page.add_inner_button(__("Project View"),()=>setView(report,"Project"),__("QFap Views"));
    report.page.add_inner_button(__("Reset QFap Filters"),()=>resetQfap(report));
  };

  function setView(report,view){
    report.set_filter_value("qfap_view",view);
    if(view==="Audit"){
      ["include_dimensions","show_remarks","show_amount_in_company_currency"].forEach(f=>{if(report.get_filter(f)) report.set_filter_value(f,1);});
    } else if(view==="Project" && report.get_filter("include_dimensions")) {
      report.set_filter_value("include_dimensions",1);
    }
    report.refresh();
  }
  function resetQfap(report){
    const values={qfap_view:"Standard",qfap_audit_search:"",qfap_min_amount:"",qfap_max_amount:"",qfap_exceptions_only:0,qfap_hide_empty_columns:1};
    Object.entries(values).forEach(([f,v])=>{if(report.get_filter(f)) report.set_filter_value(f,v);});
    report.refresh();
  }
})();
"""


def sync():
    source_dir = Path(get_module_path("Accounts")) / "report" / "general_ledger"
    target_dir = Path(frappe.get_app_path("qfap_adds")) / "qfap_adds" / "report" / "enhanced_general_ledger"
    source_js = source_dir / "general_ledger.js"
    source_html = source_dir / "general_ledger.html"
    target_js = target_dir / "enhanced_general_ledger.js"
    target_html = target_dir / "enhanced_general_ledger.html"
    if not source_js.exists():
        frappe.throw(f"General Ledger JavaScript was not found: {source_js}")
    target_dir.mkdir(parents=True, exist_ok=True)
    script = source_js.read_text(encoding="utf-8")
    script = script.replace('frappe.query_reports["General Ledger"]','frappe.query_reports["Enhanced General Ledger"]')
    script = script.replace('erpnext.utils.add_dimensions("General Ledger"','erpnext.utils.add_dimensions("Enhanced General Ledger"')
    target_js.write_text(script + ENHANCEMENT, encoding="utf-8")
    if source_html.exists():
        target_html.write_text(source_html.read_text(encoding="utf-8"), encoding="utf-8")
    frappe.clear_cache()
    print(f"Synced {source_js} -> {target_js}")
    if source_html.exists():
        print(f"Synced {source_html} -> {target_html}")
