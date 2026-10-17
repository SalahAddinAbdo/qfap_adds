from __future__ import annotations

import frappe
from frappe.modules.import_file import import_file_by_path
from frappe.utils import get_bench_path
from pathlib import Path


def sync_qfap_project_reports():
    app_path = Path(frappe.get_app_path("qfap_adds"))
    report_root = app_path / "qfap_adds" / "report"
    if not report_root.exists():
        return
    for folder in sorted(report_root.iterdir()):
        if not folder.is_dir():
            continue
        definition = folder / (folder.name + ".json")
        if definition.exists():
            import_file_by_path(str(definition), force=True, ignore_version=True)
    frappe.clear_cache()
