frappe.ui.form.on("Employee Signature Configuration", {
    setup(frm) {
        frm.set_query("document_type", () => ({ filters: { istable: 0 } }));
    },
    refresh(frm) {
        signature_load_field_catalog(frm);
        frm.add_custom_button(__("Provision Signature Fields"), async () => {
            if (frm.is_new() || frm.is_dirty()) await frm.save();
            await frappe.call({
                method: "qfap_adds.qfap_adds.api.signature_configuration.provision_fields",
                args: { configuration: frm.doc.name },
                freeze: true,
                freeze_message: __("Creating and arranging signature fields..."),
            });
            await frm.reload_doc();
            frappe.show_alert({ message: __("Signature fields are ready."), indicator: "green" });
        });
    },
    document_type(frm) {
        (frm.doc.signature_mappings || []).forEach(row => {
            ["employee_signature_field", "employee_name_field", "designation_field", "signature_date_field", "signature_image_field"].forEach(field => {
                frappe.model.set_value(row.doctype, row.name, field, "");
            });
        });
        signature_load_field_catalog(frm);
    },
    validate(frm) {
        const roles = new Set();
        (frm.doc.signature_mappings || []).forEach((row, index) => {
            if (!row.signature_role) frappe.throw(__("Signature Role is required in row {0}.", [index + 1]));
            if (roles.has(row.signature_role)) frappe.throw(__("Signature Role is repeated: {0}.", [row.signature_role]));
            roles.add(row.signature_role);
            if (!row.auto_create_fields) {
                const required = ["employee_signature_field", "employee_name_field", "designation_field", "signature_date_field", "signature_image_field"];
                required.forEach(field => {
                    if (!row[field]) frappe.throw(__("Complete the manual field mapping in row {0}.", [index + 1]));
                });
            }
        });
    },
});

frappe.ui.form.on("Employee Signature Mapping Row", {
    signature_mappings_add(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "auto_create_fields", 1);
        frappe.model.set_value(cdt, cdn, "enabled", 1);
        frappe.model.set_value(cdt, cdn, "signature_required", 1);
        signature_apply_options(frm);
    },
    signature_role(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const key = String(row.signature_role || "").toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 48);
        frappe.model.set_value(cdt, cdn, "mapping_key", key);
        if (!row.signature_role_description) frappe.model.set_value(cdt, cdn, "signature_role_description", row.signature_role || "");
    },
    auto_create_fields(frm) {
        frm.refresh_field("signature_mappings");
    },
});

async function signature_load_field_catalog(frm) {
    if (!frm.doc.document_type) return;
    const meta = await frappe.model.with_doctype(frm.doc.document_type);
    if (!meta) return;
    const fields = frappe.get_meta(frm.doc.document_type).fields || [];
    frm.__signature_catalog = {
        signature: fields.filter(df => df.fieldtype === "Link" && df.options === "Employee Signature").map(df => df.fieldname),
        employee_name: fields.filter(df => df.fieldtype === "Data").map(df => df.fieldname),
        designation: fields.filter(df => df.fieldtype === "Data" || (df.fieldtype === "Link" && df.options === "Designation")).map(df => df.fieldname),
        date: fields.filter(df => ["Date", "Datetime"].includes(df.fieldtype)).map(df => df.fieldname),
        image: fields.filter(df => ["Attach", "Attach Image"].includes(df.fieldtype)).map(df => df.fieldname),
    };
    signature_apply_options(frm);
}

function signature_apply_options(frm) {
    const catalog = frm.__signature_catalog;
    if (!catalog) return;
    const grid = frm.fields_dict.signature_mappings?.grid;
    if (!grid) return;
    const map = {
        employee_signature_field: catalog.signature,
        employee_name_field: catalog.employee_name,
        designation_field: catalog.designation,
        signature_date_field: catalog.date,
        signature_image_field: catalog.image,
    };
    Object.entries(map).forEach(([fieldname, values]) => {
        grid.update_docfield_property(fieldname, "options", ["", ...values].join("\n"));
    });
    grid.refresh();
}
