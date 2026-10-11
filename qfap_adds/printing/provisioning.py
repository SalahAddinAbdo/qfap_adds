from __future__ import annotations

from pathlib import Path

import frappe
from frappe import _
from frappe.utils import cint, now_datetime


SETTINGS_DOCTYPE = "QFAP Print Format Settings"
MANAGED_PREFIX = "QFAP Universal - "
PROFILE_TEMPLATES = {
    "QFAP Universal": "universal_dynamic_print_format.html",
}


@frappe.whitelist()
def apply_print_format_settings():
    frappe.only_for("System Manager")
    result = provision_universal_print_formats(force=True)
    frappe.msgprint(
        _("Managed print formats applied: {0} enabled/updated, {1} disabled.").format(
            result.get("enabled", 0), result.get("disabled", 0)
        ),
        alert=True,
    )
    return result


def provision_universal_print_formats(force=False):
    """Synchronize only the DocTypes selected in QFAP Print Format Settings.

    The initial migration is non-destructive: when the settings table has never
    been applied and contains no rows, existing managed formats remain unchanged.
    """
    if not frappe.db.exists("DocType", SETTINGS_DOCTYPE):
        return {"enabled": 0, "disabled": 0, "skipped": True}

    settings = frappe.get_single(SETTINGS_DOCTYPE)
    rules = list(settings.get("rules") or [])
    if not rules and not cint(settings.get("managed_once")) and not force:
        return {"enabled": 0, "disabled": 0, "skipped": True}

    enabled_names = set()
    enabled_count = 0

    for rule in rules:
        name = _format_name(rule.document_type)
        if not cint(rule.enabled):
            continue
        _validate_rule(rule)
        template = _read_template(rule.print_profile)
        html = _profile_header(rule) + "\n" + template
        _upsert_print_format(name, rule.document_type, html)
        _set_default(rule.document_type, name, cint(rule.set_as_default))
        enabled_names.add(name)
        enabled_count += 1

    disabled_count = _disable_unselected_formats(enabled_names)
    summary = _("{0} enabled/updated; {1} disabled").format(
        enabled_count, disabled_count
    )
    frappe.db.set_single_value(SETTINGS_DOCTYPE, "last_sync_on", now_datetime())
    frappe.db.set_single_value(SETTINGS_DOCTYPE, "last_sync_summary", summary)
    frappe.db.set_single_value(SETTINGS_DOCTYPE, "managed_once", 1)
    frappe.clear_cache(doctype="Print Format")
    return {"enabled": enabled_count, "disabled": disabled_count, "skipped": False}


def _validate_rule(rule):
    if not frappe.db.exists("DocType", rule.document_type):
        frappe.throw(_("Document Type does not exist: {0}").format(rule.document_type))
    meta = frappe.get_meta(rule.document_type)
    if meta.istable or meta.issingle or meta.is_virtual:
        frappe.throw(_("Document Type is not eligible for managed printing: {0}").format(rule.document_type))
    if rule.print_profile not in PROFILE_TEMPLATES:
        frappe.throw(_("Unsupported Print Profile: {0}").format(rule.print_profile))


def _read_template(profile):
    filename = PROFILE_TEMPLATES[profile]
    path = Path(__file__).parent / "templates" / filename
    return path.read_text(encoding="utf-8")


def _profile_header(rule):
    values = {
        "qfap_include_letter_head": cint(rule.include_letter_head),
        "qfap_include_workflow_status": cint(rule.include_workflow_status),
        "qfap_include_signatures": cint(rule.include_signatures),
        "qfap_include_audit_information": cint(rule.include_audit_information),
        "qfap_include_attachments": cint(rule.include_attachments),
    }
    lines = ["{# Managed by QFAP Print Format Settings. Do not edit this generated copy. #}"]
    for key, value in values.items():
        lines.append("{% set " + key + " = " + ("true" if value else "false") + " %}")
    return "\n".join(lines)


def _format_name(doctype):
    return MANAGED_PREFIX + doctype


def _upsert_print_format(name, doctype, html):
    values = {
        "doc_type": doctype,
        "print_format_type": "Jinja",
        "custom_format": 1,
        "disabled": 0,
        "html": html,
        "module": "QFap Adds",
        "standard": "No",
    }
    if frappe.db.exists("Print Format", name):
        doc = frappe.get_doc("Print Format", name)
        for fieldname, value in values.items():
            doc.set(fieldname, value)
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc({"doctype": "Print Format", "name": name, **values}).insert(
            ignore_permissions=True
        )


def _set_default(doctype, format_name, enabled):
    current = frappe.db.get_value("DocType", doctype, "default_print_format") or ""
    if enabled:
        if current != format_name:
            frappe.db.set_value(
                "DocType", doctype, "default_print_format", format_name,
                update_modified=False,
            )
    elif current == format_name:
        frappe.db.set_value(
            "DocType", doctype, "default_print_format", "",
            update_modified=False,
        )


def _disable_unselected_formats(enabled_names):
    disabled = 0
    managed = frappe.get_all(
        "Print Format",
        filters={"name": ["like", MANAGED_PREFIX + "%"]},
        fields=["name", "doc_type", "disabled"],
        limit_page_length=0,
    )
    for row in managed:
        if row.name in enabled_names:
            continue
        if not cint(row.disabled):
            frappe.db.set_value(
                "Print Format", row.name, "disabled", 1,
                update_modified=False,
            )
            disabled += 1
        _set_default(row.doc_type, row.name, False)
    return disabled
