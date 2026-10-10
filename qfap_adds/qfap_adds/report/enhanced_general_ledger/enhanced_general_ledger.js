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

// ---- QFap Adds v1.3 enhancements; ERPNext accounting behavior remains authoritative. ----
(() => {
  const reportName = "Enhanced General Ledger";
  const config = frappe.query_reports[reportName];
  if (!config || config.__qfap_adds_v13_enhanced) return;
  config.__qfap_adds_v13_enhanced = true;

  const methodBase = "qfap_adds.qfap_adds.report.enhanced_general_ledger.enhanced_general_ledger";
  const analyticalFields = ["qfap_ledger_search", "qfap_min_amount", "qfap_max_amount", "qfap_exceptions_only"];
  const layoutOptions = [
    {label: __("Standard"), value: "Standard"},
    {label: __("Compact"), value: "Compact"},
    {label: __("Audit"), value: "Audit"},
    {label: __("Project Focus"), value: "Project"},
    {label: __("Cost Center Focus"), value: "Dimension::cost_center"},
  ];

  const qfapFilters = [
    {fieldname:"qfap_view",label:__("Display Layout"),fieldtype:"Select",options:layoutOptions,default:"Standard",description:__("Changes column order and visibility only; it does not recalculate accounting groups."),on_change:()=>frappe.query_report.refresh()},
    {fieldname:"qfap_ledger_search",label:__("Ledger Search"),fieldtype:"Data",description:__("Search vouchers, parties, projects, dimensions, invoice numbers, remarks, and audit flags")},
    {fieldname:"qfap_min_amount",label:__("Minimum Amount"),fieldtype:"Currency"},
    {fieldname:"qfap_max_amount",label:__("Maximum Amount"),fieldtype:"Currency"},
    {fieldname:"qfap_exceptions_only",label:__("Audit Exceptions Only"),fieldtype:"Check",default:0},
    {fieldname:"qfap_hide_empty_columns",label:__("Hide Empty Columns"),fieldtype:"Check",default:1},
  ];
  const existing = new Set((config.filters || []).map(filter => filter.fieldname));
  qfapFilters.forEach(filter => { if (!existing.has(filter.fieldname)) config.filters.push(filter); });
  qfapFilters.filter(filter => analyticalFields.includes(filter.fieldname)).forEach(filter => {
    filter.on_change = () => handleAnalyticalConflict(filter.fieldname);
  });

  const originalFormatter = config.formatter;
  config.formatter = function(value,row,column,data,defaultFormatter) {
    let output = originalFormatter ? originalFormatter.call(this,value,row,column,data,defaultFormatter) : defaultFormatter(value,row,column,data);
    if (data && data.qfap_dimension_group_header) {
      return `<span style="font-weight:700;color:var(--text-color);display:block;padding:5px 7px;background:var(--subtle-fg);border-radius:6px">${frappe.utils.escape_html(String(value || ""))}</span>`;
    }
    if (data && column.qfap_link_doctype && column.qfap_code_field) {
      const code = data[column.qfap_code_field];
      if (code) {
        const title = data[column.qfap_title_field] || code;
        const route = `/app/${frappe.router.slug(column.qfap_link_doctype)}/${encodeURIComponent(code)}`;
        output = `<a href="${route}" title="${frappe.utils.escape_html(String(title))}" class="qfap-dimension-link">${frappe.utils.escape_html(String(value || code))}</a>`;
      }
    }
    if (data && column.fieldname === "qfap_audit_flags" && value) {
      output = `<span class="indicator-pill orange" title="${frappe.utils.escape_html(String(value))}">${frappe.utils.escape_html(String(value))}</span>`;
    }
    return output;
  };

  const originalOnload = config.onload;
  config.onload = function(report) {
    if (originalOnload) originalOnload.call(this, report);
    initializeDimensions(report);
    report.page.add_inner_button(__("Standard Layout"),()=>setLayout(report,"Standard"),__("QFap Layouts"));
    report.page.add_inner_button(__("Compact Layout"),()=>setLayout(report,"Compact"),__("QFap Layouts"));
    report.page.add_inner_button(__("Audit Layout"),()=>setLayout(report,"Audit"),__("QFap Layouts"));
    report.page.add_inner_button(__("Project Focus"),()=>setLayout(report,"Project"),__("QFap Layouts"));
    report.page.add_inner_button(__("Reset QFap Filters"),()=>resetQfap(report));
  };

  async function initializeDimensions(report) {
    const response = await frappe.call({method:`${methodBase}.get_qfap_dimension_config`});
    const dimensions = response.message || [];
    report.qfap_dimensions = dimensions;
    await waitForDimensionFilters(report, dimensions, 0);
    addDimensionLayouts(report, dimensions);
    addDimensionCategories(report, dimensions);
    configureTreeDescriptions(report, dimensions);
    configureBudgetLine(report, dimensions);
    configureCategorizeConflict(report);
  }

  function waitForDimensionFilters(report, dimensions, attempt) {
    const missing = dimensions.filter(d => !report.get_filter(d.fieldname));
    if (!missing.length || attempt >= 20) return Promise.resolve();
    return new Promise(resolve => setTimeout(() => resolve(waitForDimensionFilters(report, dimensions, attempt + 1)), 250));
  }

  function addDimensionLayouts(report, dimensions) {
    const options = [...layoutOptions];
    dimensions.forEach(d => {
      if (!["project","cost_center"].includes(d.fieldname)) {
        options.push({label: __(`${d.label} Focus`), value:`Dimension::${d.fieldname}`});
      }
    });
    const filter = report.get_filter("qfap_view");
    if (filter) { filter.df.options = options; filter.refresh(); }
  }

  function addDimensionCategories(report, dimensions) {
    const filter = report.get_filter("categorize_by");
    if (!filter) return;
    const options = Array.isArray(filter.df.options) ? [...filter.df.options] : String(filter.df.options || "").split("\n");
    const values = new Set(options.map(option => typeof option === "object" ? option.value : option));
    const additions = [
      {fieldname:"project",label:__("Project")},
      {fieldname:"cost_center",label:__("Cost Center")},
      ...dimensions.filter(d => !["project","cost_center"].includes(d.fieldname)),
    ];
    additions.forEach(d => {
      const value = `Categorize by Dimension::${d.fieldname}`;
      if (!values.has(value)) options.push({label:__(`Categorize by ${d.label}`),value});
    });
    filter.df.options = options;
    filter.refresh();
  }

  function configureTreeDescriptions(report, dimensions) {
    dimensions.filter(d => d.is_tree).forEach(d => {
      const filter = report.get_filter(d.fieldname);
      if (!filter) return;
      filter.df.description = __("Selecting a parent includes the selected node and all descendants.");
      filter.refresh();
    });
  }

  function configureBudgetLine(report, dimensions) {
    const dimension = dimensions.find(d => d.is_budget_line);
    if (!dimension) return;
    const budgetFilter = report.get_filter(dimension.fieldname);
    const projectFilter = report.get_filter("project");
    if (!budgetFilter || !projectFilter) return;

    budgetFilter.df.get_data = txt => {
      const projects = normalizedValues(report.get_filter_value("project"));
      if (!projects.length) {
        frappe.show_alert({message:__("Select a Project first to load its Budget Lines."),indicator:"orange"});
        return [];
      }
      return frappe.call({method:`${methodBase}.get_budget_line_options`,args:{txt:txt || "",projects,limit:50}}).then(r => r.message || []);
    };

    const originalProjectChange = projectFilter.df.on_change;
    projectFilter.df.on_change = function() {
      if (originalProjectChange) originalProjectChange.apply(this, arguments);
      if (normalizedValues(report.get_filter_value(dimension.fieldname)).length) {
        report.set_filter_value(dimension.fieldname, []);
        frappe.show_alert({message:__("Budget Line was cleared because the Project filter changed."),indicator:"blue"});
      }
      updateBudgetControl(report, budgetFilter);
    };
    updateBudgetControl(report, budgetFilter);
  }

  function updateBudgetControl(report, budgetFilter) {
    const enabled = normalizedValues(report.get_filter_value("project")).length > 0;
    budgetFilter.df.hidden = 0;
    budgetFilter.df.description = enabled
      ? __("Only Budget Lines linked to the selected Project(s) are shown. Selecting a group includes descendants.")
      : __("Select a Project first to load its Budget Lines.");
    budgetFilter.refresh();
    if (budgetFilter.$input) budgetFilter.$input.prop("disabled", !enabled);
    if (!enabled) report.set_filter_value(budgetFilter.df.fieldname, []);
  }

  function configureCategorizeConflict(report) {
    const filter = report.get_filter("categorize_by");
    if (!filter) return;
    const original = filter.df.on_change;
    filter.df.on_change = function() {
      if (original) original.apply(this, arguments);
      if (report.get_filter_value("categorize_by") && hasAnalyticalValues(report)) {
        frappe.confirm(
          __("Categorize by requires clearing QFap analytical filters. Clear them and continue?"),
          () => { clearAnalytical(report); report.refresh(); },
          () => report.set_filter_value("categorize_by", "")
        );
      }
    };
  }

  function handleAnalyticalConflict(changedField) {
    const report = frappe.query_report;
    if (!report.get_filter_value(changedField) || !report.get_filter_value("categorize_by")) return;
    frappe.confirm(
      __("Analytical filters require an ungrouped ledger. Clear Categorize by and continue?"),
      () => { report.set_filter_value("categorize_by", ""); report.refresh(); },
      () => report.set_filter_value(changedField, changedField === "qfap_exceptions_only" ? 0 : "")
    );
  }

  function normalizedValues(value) {
    if (!value) return [];
    if (!Array.isArray(value)) value = String(value).split(",");
    return value.map(item => typeof item === "object" ? item.value : item).filter(Boolean);
  }

  function hasAnalyticalValues(report) {
    return analyticalFields.some(fieldname => Boolean(report.get_filter_value(fieldname)));
  }

  function clearAnalytical(report) {
    analyticalFields.forEach(fieldname => report.set_filter_value(fieldname, fieldname === "qfap_exceptions_only" ? 0 : ""));
  }

  function setLayout(report, value) {
    report.set_filter_value("qfap_view", value);
    if (value === "Audit") {
      ["include_dimensions","show_remarks","show_amount_in_company_currency"].forEach(fieldname => {if(report.get_filter(fieldname)) report.set_filter_value(fieldname,1);});
    } else if ((value === "Project" || String(value).startsWith("Dimension::")) && report.get_filter("include_dimensions")) {
      report.set_filter_value("include_dimensions",1);
    }
    report.refresh();
  }

  function resetQfap(report) {
    const values={qfap_view:"Standard",qfap_ledger_search:"",qfap_min_amount:"",qfap_max_amount:"",qfap_exceptions_only:0,qfap_hide_empty_columns:1};
    Object.entries(values).forEach(([fieldname,value]) => {if(report.get_filter(fieldname)) report.set_filter_value(fieldname,value);});
    report.refresh();
  }
})();
