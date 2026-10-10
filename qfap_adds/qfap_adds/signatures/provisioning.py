from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


MAPPING_FIELDS = (
    "employee_signature_field",
    "employee_name_field",
    "designation_field",
    "signature_date_field",
    "signature_notes_field",
    "signature_image_field",
)

SIGNATURE_SUFFIXES = (
    "signature_section",
    "employee_signature",
    "employee_name",
    "designation",
    "column_1",
    "signature_date",
    "signature_notes",
    "column_2",
    "signature_image",
)


def validate_configuration(doc):
    if not doc.document_type or not frappe.db.exists("DocType", doc.document_type):
        frappe.throw(_("A valid Document Type is required."))
    if doc.enabled and not doc.signature_mappings:
        frappe.throw(_("At least one Signature Mapping is required."))

    roles = set()
    keys = set()
    for row in doc.signature_mappings or []:
        if not row.signature_role:
            frappe.throw(_("Signature Role is required in row {0}.").format(row.idx))

        row.mapping_key = _role_key(row.signature_role)
        if row.signature_role in roles or row.mapping_key in keys:
            frappe.throw(_("Duplicate Signature Role or Mapping Key in row {0}.").format(row.idx))
        roles.add(row.signature_role)
        keys.add(row.mapping_key)

        if not row.auto_create_fields:
            missing = [fieldname for fieldname in MAPPING_FIELDS if not row.get(fieldname)]
            if missing:
                frappe.throw(
                    _("Missing manual field mapping in row {0}: {1}").format(
                        row.idx, ", ".join(missing)
                    )
                )
            _validate_manual_fields(doc.document_type, row)


def provision_signature_fields(doc):
    rows = list(doc.signature_mappings or [])
    anchor = _signature_anchor(doc.document_type, rows)
    generated_order = []

    for row in rows:
        row.mapping_key = _role_key(row.signature_role)
        if row.auto_create_fields:
            anchor, ordered_fields = _provision_row(doc.document_type, row, anchor)
            generated_order.extend(ordered_fields)
        else:
            _apply_visibility(doc.document_type, row, bool(row.hide_generated_fields))

    if generated_order:
        _reorder_existing_custom_fields(doc.document_type, generated_order)

    frappe.clear_cache(doctype=doc.document_type)


def _provision_row(doctype, row, anchor):
    key = _role_key(row.signature_role)
    prefix = "custom_" + key
    names = {
        "section": prefix + "_signature_section",
        "signature": prefix + "_employee_signature",
        "employee_name": prefix + "_employee_name",
        "designation": prefix + "_designation",
        "column_1": prefix + "_column_1",
        "date": prefix + "_signature_date",
        "notes": prefix + "_signature_notes",
        "column_2": prefix + "_column_2",
        "image": prefix + "_signature_image",
    }
    hidden = 1 if row.hide_generated_fields else 0
    specs = [
        _spec(names["section"], row.signature_role_description or row.signature_role, "Section Break", anchor, hidden, collapsible=1),
        _spec(names["signature"], "Employee Signature", "Link", names["section"], hidden, options="Employee Signature", print_hide=1),
        _spec(names["employee_name"], "Employee Name", "Data", names["signature"], hidden),
        _spec(names["designation"], "Designation", "Link", names["employee_name"], hidden, options="Designation"),
        _spec(names["column_1"], "", "Column Break", names["designation"], hidden),
        _spec(names["date"], "Signature Date", "Date", names["column_1"], hidden),
        _spec(names["notes"], "Signature Notes", "Small Text", names["date"], hidden),
        _spec(names["column_2"], "", "Column Break", names["notes"], hidden),
        _spec(names["image"], "Signature Image", "Attach Image", names["column_2"], hidden),
    ]

    meta = frappe.get_meta(doctype)
    missing = [spec for spec in specs if not meta.has_field(spec["fieldname"])]
    if missing:
        create_custom_fields({doctype: missing}, update=True)
        frappe.clear_cache(doctype=doctype)

    _sync_generated_fields(doctype, specs)

    row.employee_signature_field = names["signature"]
    row.employee_name_field = names["employee_name"]
    row.designation_field = names["designation"]
    row.signature_date_field = names["date"]
    row.signature_notes_field = names["notes"]
    row.signature_image_field = names["image"]
    _save_row_mapping(row)
    _apply_visibility(doctype, row, bool(row.hide_generated_fields), names)

    return names["image"], [spec["fieldname"] for spec in specs]


def _spec(fieldname, label, fieldtype, insert_after, hidden, options="", collapsible=0, print_hide=0):
    value = {
        "fieldname": fieldname,
        "label": label,
        "fieldtype": fieldtype,
        "insert_after": insert_after,
        "options": options,
        "hidden": hidden,
        "collapsible": collapsible,
        "print_hide": print_hide,
    }
    if fieldtype not in ("Section Break", "Column Break"):
        value.update({"read_only": 1, "allow_on_submit": 1, "no_copy": 1})
    return value


def _sync_generated_fields(doctype, specs):
    properties = (
        "label",
        "fieldtype",
        "options",
        "insert_after",
        "read_only",
        "allow_on_submit",
        "no_copy",
        "print_hide",
        "hidden",
        "collapsible",
    )

    for spec in specs:
        name = frappe.db.get_value(
            "Custom Field",
            {"dt": doctype, "fieldname": spec["fieldname"]},
            "name",
        )
        if not name:
            continue

        values = {}
        for prop in properties:
            default = "" if prop in ("label", "options", "insert_after") else 0
            values[prop] = spec.get(prop, default)

        # db.set_value is intentional here. It updates every old field even when
        # a stale in-memory Custom Field document still contains its former layout.
        frappe.db.set_value("Custom Field", name, values, update_modified=False)


def _reorder_existing_custom_fields(doctype, generated_order):
    """Rebuild the stored idx order after fixing every insert_after chain.

    Old generated fields may keep historical idx values even after insert_after
    is corrected. New fields do not have that history, which is why only new
    signature blocks appeared correctly. This routine removes all generated
    signature fields from the current meta order, inserts the complete ordered
    chain at the first signature section position, and writes deterministic idx
    values for every Custom Field in the resulting form order.
    """
    frappe.clear_cache(doctype=doctype)
    meta = frappe.get_meta(doctype, cached=False)
    generated = set(generated_order)
    current = [df.fieldname for df in meta.fields if df.fieldname]

    section_fields = [name for name in generated_order if name.endswith("_signature_section")]
    section_positions = [current.index(name) for name in section_fields if name in current]
    if section_positions:
        insertion_index = min(section_positions)
    else:
        generated_positions = [current.index(name) for name in generated_order if name in current]
        insertion_index = min(generated_positions) if generated_positions else len(current)

    without_generated = [name for name in current if name not in generated]
    insertion_index = min(insertion_index, len(without_generated))
    final_order = (
        without_generated[:insertion_index]
        + list(generated_order)
        + without_generated[insertion_index:]
    )

    custom_fields = frappe.get_all(
        "Custom Field",
        filters={"dt": doctype},
        fields=["name", "fieldname"],
    )
    by_fieldname = {row.fieldname: row.name for row in custom_fields}

    for idx, fieldname in enumerate(final_order, start=1):
        custom_name = by_fieldname.get(fieldname)
        if custom_name:
            frappe.db.set_value("Custom Field", custom_name, "idx", idx, update_modified=False)

    frappe.clear_cache(doctype=doctype)


def _save_row_mapping(row):
    values = {"mapping_key": row.mapping_key}
    values.update({fieldname: row.get(fieldname) for fieldname in MAPPING_FIELDS})
    frappe.db.set_value(row.doctype, row.name, values, update_modified=False)


def _apply_visibility(doctype, row, hidden, names=None):
    fieldnames = list(names.values()) if names else [row.get(name) for name in MAPPING_FIELDS]
    for fieldname in [name for name in fieldnames if name]:
        custom_name = frappe.db.get_value(
            "Custom Field", {"dt": doctype, "fieldname": fieldname}, "name"
        )
        if custom_name:
            frappe.db.set_value(
                "Custom Field", custom_name, "hidden", 1 if hidden else 0, update_modified=False
            )


def _validate_manual_fields(doctype, row):
    expected = {
        row.employee_signature_field: (("Link",), "Employee Signature"),
        row.employee_name_field: (("Data",), None),
        row.designation_field: (("Data", "Link"), None),
        row.signature_date_field: (("Date", "Datetime"), None),
        row.signature_notes_field: (("Data", "Small Text", "Text"), None),
        row.signature_image_field: (("Attach", "Attach Image"), None),
    }
    meta = frappe.get_meta(doctype)
    for fieldname, (fieldtypes, options) in expected.items():
        df = meta.get_field(fieldname)
        if not df or df.fieldtype not in fieldtypes:
            frappe.throw(_("Field {0} is missing or has an incompatible type.").format(fieldname))
        if options and df.options != options:
            frappe.throw(_("Field {0} must link to {1}.").format(fieldname, options))


def _role_key(role):
    key = re.sub(r"[^a-z0-9_]+", "_", (role or "").strip().lower()).strip("_")
    if not key:
        frappe.throw(_("Signature Role cannot generate a valid Mapping Key."))
    return key[:48]


def _signature_anchor(doctype, rows):
    """Use the field before the earliest signature section as the stable anchor."""
    meta = frappe.get_meta(doctype)
    fields = [df.fieldname for df in meta.fields if df.fieldname]
    sections = []

    for row in rows:
        key = _role_key(row.signature_role)
        section = "custom_" + key + "_signature_section"
        if section in fields:
            sections.append(section)

    if sections:
        first_index = min(fields.index(section) for section in sections)
        return fields[first_index - 1] if first_index > 0 else ""

    # No section exists yet. Place the first block after the last existing field.
    return fields[-1] if fields else ""
