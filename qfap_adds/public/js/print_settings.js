frappe.ui.form.on("Print Settings", {
    setup(frm) {
        // qorg_rules is a Table field on the standard Print Settings Single.
        // Configure its child Link query through the supported child-table API.
        frm.set_query("document_type", "qorg_rules", () => ({
            filters: {
                istable: 0,
                issingle: 0,
                is_virtual: 0,
            },
        }));
    },

    qorg_apply_formats(frm) {
        frappe.call({
            method: "qfap_adds.qfap_adds.project_management.print_settings_integration.apply_print_formats",
            freeze: true,
            freeze_message: __("Applying managed print formats..."),
            callback() {
                frm.reload_doc();
            },
        });
    },
});
