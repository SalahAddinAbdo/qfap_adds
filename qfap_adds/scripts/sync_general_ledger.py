from __future__ import annotations

from pathlib import Path

import frappe
from frappe.modules import get_module_path


ENHANCEMENT = """

// ---- QFap Adds enhancements; ERPNext filters and behaviors remain intact. ----
(() => {
  const config = frappe.query_reports["Enhanced General Ledger"];

  if (!config || config.__qfap_adds_enhanced) {
    return;
  }

  config.__qfap_adds_enhanced = true;

  const original_formatter = config.formatter;

  config.formatter = function (
    value,
    row,
    column,
    data,
    default_formatter
  ) {
    let output = original_formatter
      ? original_formatter.call(
          this,
          value,
          row,
          column,
          data,
          default_formatter
        )
      : default_formatter(value, row, column, data);

    if (
      data &&
      column.fieldname === "project" &&
      data.project_code
    ) {
      const route =
        `/app/project/${encodeURIComponent(data.project_code)}`;

      const title = frappe.utils.escape_html(
        data.project_name || data.project_code
      );

      const label = frappe.utils.escape_html(
        String(value || data.project_code)
      );

      output = `<a href="${route}" title="${title}" class="qfap-project-link">${label}</a>`;
    }

    return output;
  };

  const original_onload = config.onload;

  config.onload = function (report) {
    if (original_onload) {
      original_onload.call(this, report);
    }

    report.page.add_inner_button(
      __("Audit View"),
      () => {
        const values = {
          include_dimensions: 1,
          show_remarks: 1,
          show_amount_in_company_currency: 1,
        };

        Object.entries(values).forEach(([fieldname, value]) => {
          if (report.get_filter(fieldname)) {
            report.set_filter_value(fieldname, value);
          }
        });

        report.refresh();
      },
      __("View")
    );

    report.page.add_inner_button(
      __("Standard View"),
      () => {
        [
          "show_remarks",
          "show_amount_in_company_currency",
          "add_values_in_transaction_currency",
        ].forEach((fieldname) => {
          if (report.get_filter(fieldname)) {
            report.set_filter_value(fieldname, 0);
          }
        });

        report.refresh();
      },
      __("View")
    );
  };
})();
"""


def sync():
    """Synchronize the enhanced report UI with installed ERPNext General Ledger."""

    source_dir = (
        Path(get_module_path("Accounts"))
        / "report"
        / "general_ledger"
    )

    target_dir = (
        Path(frappe.get_app_path("qfap_adds"))
        / "qfap_adds"
        / "report"
        / "enhanced_general_ledger"
    )

    source_js = source_dir / "general_ledger.js"
    source_html = source_dir / "general_ledger.html"

    target_js = target_dir / "enhanced_general_ledger.js"
    target_html = target_dir / "enhanced_general_ledger.html"

    if not source_js.exists():
        frappe.throw(
            f"General Ledger JavaScript was not found: {source_js}"
        )

    target_dir.mkdir(parents=True, exist_ok=True)

    script = source_js.read_text(encoding="utf-8")

    script = script.replace(
        'frappe.query_reports["General Ledger"]',
        'frappe.query_reports["Enhanced General Ledger"]',
    )

    script = script.replace(
        'erpnext.utils.add_dimensions("General Ledger"',
        'erpnext.utils.add_dimensions("Enhanced General Ledger"',
    )

    script += ENHANCEMENT

    target_js.write_text(
        script,
        encoding="utf-8",
    )

    if source_html.exists():
        target_html.write_text(
            source_html.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    frappe.clear_cache()

    print(f"Synced {source_js} -> {target_js}")

    if source_html.exists():
        print(f"Synced {source_html} -> {target_html}")
