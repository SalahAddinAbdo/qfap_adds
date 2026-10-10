// ============================================================
// Employee Signature Configuration
// Dynamic field selectors based on the selected Document Type
// ============================================================

frappe.ui.form.on("Employee Signature Configuration", {
    setup(frm) {
        frm.__signature_document_type = frm.doc.document_type || "";
    },

    async onload(frm) {
        frm.__signature_document_type = frm.doc.document_type || "";
        await signature_configuration_load_fields(frm);
    },

    async refresh(frm) {
        frm.__signature_document_type = frm.doc.document_type || "";
        await signature_configuration_load_fields(frm);
    },

    document_type(frm) {
        signature_configuration_handle_document_type_change(frm);
    },

    signature_mappings_add(frm, cdt, cdn) {
        signature_configuration_apply_options(frm);
        signature_configuration_initialize_row(frm, cdt, cdn);
    },

    validate(frm) {
        signature_configuration_validate_rows(frm);
    }
});

frappe.ui.form.on("Employee Signature Mapping Row", {
    employee_signature_field(frm, cdt, cdn) {
        signature_configuration_signature_field_changed(frm, cdt, cdn);
    },

    signature_mappings_add(frm, cdt, cdn) {
        signature_configuration_apply_options(frm);
        signature_configuration_initialize_row(frm, cdt, cdn);
    }
});

async function signature_configuration_handle_document_type_change(frm) {
    if (frm.__changing_signature_doctype) return;

    const previous = frm.__signature_document_type || "";
    const next = frm.doc.document_type || "";

    if (previous === next) {
        await signature_configuration_load_fields(frm);
        return;
    }

    const has_rows = (frm.doc.signature_mappings || []).length > 0;

    if (!has_rows) {
        frm.__signature_document_type = next;
        await signature_configuration_load_fields(frm);
        return;
    }

    frappe.confirm(
        __(
            "Changing the Document Type will clear all existing Signature Mappings. Continue?"
        ),
        async () => {
            frm.clear_table("signature_mappings");
            frm.refresh_field("signature_mappings");
            frm.__signature_document_type = next;
            await signature_configuration_load_fields(frm);
        },
        async () => {
            frm.__changing_signature_doctype = true;
            await frm.set_value("document_type", previous);
            frm.__changing_signature_doctype = false;
            await signature_configuration_load_fields(frm);
        }
    );
}

async function signature_configuration_load_fields(frm) {
    const doctype = frm.doc.document_type;

    frm.__signature_field_catalog = {
        signature: [],
        designation: [],
        date: [],
        image: [],
        labels: {}
    };

    if (!doctype) {
        signature_configuration_apply_options(frm);
        return;
    }

    try {
        await frappe.model.with_doctype(doctype);
        const meta = frappe.get_meta(doctype);
        const fields = (meta && meta.fields) || [];

        fields.forEach(df => {
            if (!df.fieldname || df.hidden || df.is_virtual) return;

            frm.__signature_field_catalog.labels[df.fieldname] =
                df.label || df.fieldname;

            if (
                df.fieldtype === "Link" &&
                df.options === "Employee Signature"
            ) {
                frm.__signature_field_catalog.signature.push(df.fieldname);
            }

            if (
                df.fieldtype === "Data" ||
                (
                    df.fieldtype === "Link" &&
                    df.options === "Designation"
                )
            ) {
                frm.__signature_field_catalog.designation.push(df.fieldname);
            }

            if (["Date", "Datetime"].includes(df.fieldtype)) {
                frm.__signature_field_catalog.date.push(df.fieldname);
            }

            if (df.fieldtype === "Attach Image") {
                frm.__signature_field_catalog.image.push(df.fieldname);
            }
        });

        signature_configuration_sort_catalog(frm);
        signature_configuration_apply_options(frm);
        signature_configuration_clean_invalid_values(frm);
    } catch (error) {
        console.error("Unable to load target DocType fields", error);
        frappe.msgprint({
            title: __("Employee Signature Configuration"),
            message: __("The selected Document Type fields could not be loaded."),
            indicator: "red"
        });
    }
}

function signature_configuration_sort_catalog(frm) {
    const catalog = frm.__signature_field_catalog;
    const by_label = (a, b) => {
        const a_label = catalog.labels[a] || a;
        const b_label = catalog.labels[b] || b;
        return a_label.localeCompare(b_label);
    };

    catalog.signature.sort(by_label);
    catalog.designation.sort(by_label);
    catalog.date.sort(by_label);
    catalog.image.sort(by_label);
}

function signature_configuration_option_lines(frm, fieldnames) {
    const labels = frm.__signature_field_catalog?.labels || {};

    return [""]
        .concat(fieldnames || [])
        .map(fieldname => {
            if (!fieldname) return "";
            const label = labels[fieldname] || fieldname;
            return label === fieldname
                ? fieldname
                : `${fieldname}`;
        })
        .join("\n");
}

function signature_configuration_apply_options(frm) {
    const catalog = frm.__signature_field_catalog || {
        signature: [], designation: [], date: [], image: []
    };
    const grid = frm.fields_dict.signature_mappings?.grid;

    if (!grid) return;

    grid.update_docfield_property(
        "employee_signature_field",
        "options",
        signature_configuration_option_lines(frm, catalog.signature)
    );
    grid.update_docfield_property(
        "designation_field",
        "options",
        signature_configuration_option_lines(frm, catalog.designation)
    );
    grid.update_docfield_property(
        "signature_date_field",
        "options",
        signature_configuration_option_lines(frm, catalog.date)
    );
    grid.update_docfield_property(
        "signature_image_field",
        "options",
        signature_configuration_option_lines(frm, catalog.image)
    );

    frm.refresh_field("signature_mappings");
}

function signature_configuration_initialize_row(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.signature_required === undefined || row.signature_required === null) {
        frappe.model.set_value(cdt, cdn, "signature_required", 1);
    }
    if (row.enabled === undefined || row.enabled === null) {
        frappe.model.set_value(cdt, cdn, "enabled", 1);
    }
}

async function signature_configuration_signature_field_changed(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const fieldname = row.employee_signature_field || "";
    const labels = frm.__signature_field_catalog?.labels || {};

    await frappe.model.set_value(cdt, cdn, "mapping_key", fieldname);
    await frappe.model.set_value(
        cdt,
        cdn,
        "signature_role_description",
        fieldname ? (labels[fieldname] || fieldname) : ""
    );
}

function signature_configuration_clean_invalid_values(frm) {
    const catalog = frm.__signature_field_catalog;
    if (!catalog) return;

    const allowed = {
        employee_signature_field: new Set(catalog.signature),
        designation_field: new Set(catalog.designation),
        signature_date_field: new Set(catalog.date),
        signature_image_field: new Set(catalog.image)
    };

    (frm.doc.signature_mappings || []).forEach(row => {
        Object.keys(allowed).forEach(fieldname => {
            const value = row[fieldname];
            if (value && !allowed[fieldname].has(value)) {
                frappe.model.set_value(
                    row.doctype,
                    row.name,
                    fieldname,
                    ""
                );
            }
        });
    });
}

function signature_configuration_validate_rows(frm) {
    if (!frm.doc.document_type) {
        frappe.throw(__("Document Type is required."));
    }

    if (frm.doc.enabled && !(frm.doc.signature_mappings || []).length) {
        frappe.throw(
            __("At least one Signature Mapping is required when the configuration is enabled.")
        );
    }

    const keys = new Set();
    const signature_fields = new Set();

    (frm.doc.signature_mappings || []).forEach((row, index) => {
        if (!row.enabled) return;

        if (!row.employee_signature_field) {
            frappe.throw(
                __("Employee Signature Field is required in row {0}.", [index + 1])
            );
        }

        const key = row.mapping_key || row.employee_signature_field;

        if (keys.has(key)) {
            frappe.throw(__("Duplicate Mapping Key: {0}.", [key]));
        }

        if (signature_fields.has(row.employee_signature_field)) {
            frappe.throw(
                __("Employee Signature Field is selected more than once: {0}.", [row.employee_signature_field])
            );
        }

        keys.add(key);
        signature_fields.add(row.employee_signature_field);
    });
}

