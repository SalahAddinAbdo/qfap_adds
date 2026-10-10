// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Enhanced General Ledger"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "finance_book",
			label: __("Finance Book"),
			fieldtype: "Link",
			options: "Finance Book",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
			width: "60px",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
			width: "60px",
		},
		{
			fieldname: "account",
			label: __("Account"),
			fieldtype: "MultiSelectList",
			options: "Account",
			get_data: function (txt) {
				return frappe.db.get_link_options("Account", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "voucher_no",
			label: __("Voucher No"),
			fieldtype: "Data",
			on_change: function () {
				frappe.query_report.set_filter_value("categorize_by", "Categorize by Voucher (Consolidated)");
			},
		},
		{
			fieldname: "against_voucher_no",
			label: __("Against Voucher No"),
			fieldtype: "Data",
		},
		{
			fieldtype: "Break",
		},
		{
			fieldname: "party_type",
			label: __("Party Type"),
			fieldtype: "Autocomplete",
			options: Object.keys(frappe.boot.party_account_types),
			on_change: function () {
				frappe.query_report.set_filter_value("party", []);
			},
		},
		{
			fieldname: "party",
			label: __("Party"),
			fieldtype: "MultiSelectList",
			options: "party_type",
			depends_on: "party_type",
			get_data: function (txt) {
				if (!frappe.query_report.filters) return;

				let party_type = frappe.query_report.get_filter_value("party_type");
				if (!party_type) return;

				return frappe.db.get_link_options(party_type, txt);
			},
			on_change: function () {
				var party_type = frappe.query_report.get_filter_value("party_type");
				var parties = frappe.query_report.get_filter_value("party");

				if (!party_type || parties.length === 0 || parties.length > 1) {
					frappe.query_report.set_filter_value("party_name", "");
					frappe.query_report.set_filter_value("tax_id", "");
					return;
				} else {
					var party = parties[0];
					var fieldname = erpnext.utils.get_party_name(party_type) || "name";
					frappe.db.get_value(party_type, party, fieldname, function (value) {
						frappe.query_report.set_filter_value("party_name", value[fieldname]);
					});

					if (party_type === "Customer" || party_type === "Supplier") {
						frappe.db.get_value(party_type, party, "tax_id", function (value) {
							frappe.query_report.set_filter_value("tax_id", value["tax_id"]);
						});
					}
				}
			},
		},
		{
			fieldname: "party_name",
			label: __("Party Name"),
			fieldtype: "Data",
			hidden: 1,
		},
		{
			fieldname: "categorize_by",
			label: __("Categorize by"),
			fieldtype: "Select",
			options: [
				"",
				{
					label: __("Categorize by Voucher"),
					value: "Categorize by Voucher",
				},
				{
					label: __("Categorize by Voucher (Consolidated)"),
					value: "Categorize by Voucher (Consolidated)",
				},
				{
					label: __("Categorize by Account"),
					value: "Categorize by Account",
				},
				{
					label: __("Categorize by Party"),
					value: "Categorize by Party",
				},
			],
			default: "Categorize by Voucher (Consolidated)",
		},
		{
			fieldname: "tax_id",
			label: __("Tax Id"),
			fieldtype: "Data",
			hidden: 1,
		},
		{
			fieldname: "presentation_currency",
			label: __("Currency"),
			fieldtype: "Select",
			options: erpnext.get_presentation_currency_list(),
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "MultiSelectList",
			options: "Cost Center",
			get_data: function (txt) {
				return frappe.db.get_link_options("Cost Center", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "MultiSelectList",
			options: "Project",
			get_data: function (txt) {
				return frappe.db.get_link_options("Project", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "include_dimensions",
			label: __("Consider Accounting Dimensions"),
			fieldtype: "Check",
			default: frappe.boot.sysdefaults.disable_include_dimensions ? 0 : 1,
		},
		{
			fieldname: "disable_opening_balance_calculation",
			label: __("Disable Opening Balance Calculation"),
			fieldtype: "Check",
		},
		{
			fieldname: "show_opening_entries",
			label: __("Show Opening Entries"),
			fieldtype: "Check",
			depends_on: "eval: !doc.disable_opening_balance_calculation",
		},
		{
			fieldname: "include_default_book_entries",
			label: __("Include Default FB Entries"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "show_cancelled_entries",
			label: __("Show Cancelled Entries"),
			fieldtype: "Check",
		},
		{
			fieldname: "show_net_values_in_party_account",
			label: __("Show Net Values in Party Account"),
			fieldtype: "Check",
		},
		{
			fieldname: "show_amount_in_company_currency",
			label: __("Show Credit / Debit in Company Currency"),
			fieldtype: "Check",
		},
		{
			fieldname: "add_values_in_transaction_currency",
			label: __("Add Columns in Transaction Currency"),
			fieldtype: "Check",
		},
		{
			fieldname: "show_remarks",
			label: __("Show Remarks"),
			fieldtype: "Check",
		},
		{
			fieldname: "ignore_err",
			label: __("Ignore Exchange Rate Revaluation and Gain / Loss Journals"),
			fieldtype: "Check",
		},
		{
			fieldname: "ignore_cr_dr_notes",
			label: __("Ignore System Generated Credit / Debit Notes"),
			fieldtype: "Check",
		},
	],
	collapsible_filters: true,
	seperate_check_filters: true,
};

erpnext.utils.add_dimensions("Enhanced General Ledger", 15);


// ---- QFap Adds v1.1 enhancements; ERPNext filters and behavior remain intact. ----
(() => {
  const reportName = "Enhanced General Ledger";
  const config = frappe.query_reports[reportName];
  if (!config || config.__qfap_adds_v11_enhanced) return;
  config.__qfap_adds_v11_enhanced = true;

  const filters = [
    {fieldname:"qfap_view",label:__("QFap View"),fieldtype:"Select",options:["Standard","Compact","Audit","Project"].join("\n"),default:"Standard",on_change:()=>frappe.query_report.refresh()},
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
