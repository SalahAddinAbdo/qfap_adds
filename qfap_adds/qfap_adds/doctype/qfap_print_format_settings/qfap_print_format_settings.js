frappe.ui.form.on("QFAP Print Format Settings", {
    setup(frm) {
        const field = frm.fields_dict.rules?.grid?.get_field("document_type");
        if (field) {
            field.get_query = () => ({
                filters: {
                    istable: 0,
                    issingle: 0,
                    is_virtual: 0,
                },
            });
        }
    },

    apply_formats(frm) {
        frappe.call({
            method: "qfap_adds.printing.provisioning.apply_print_format_settings",
            freeze: true,
            freeze_message: __("Applying managed print formats..."),
            callback() {
                frm.reload_doc();
            },
        });
    },
});
