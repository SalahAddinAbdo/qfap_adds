frappe.ui.form.on("Print Settings", {
    setup(frm) {
        qorg_configure_rules_grid(frm);
    },

    refresh(frm) {
        qorg_configure_rules_grid(frm);
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

function qorg_configure_rules_grid(frm) {
    const grid = frm.fields_dict.qorg_rules?.grid;
    if (!grid || grid.__qorg_configured) return;
    grid.__qorg_configured = true;

    const documentType = grid.get_field("document_type");
    if (documentType) {
        documentType.get_query = () => ({
            filters: { istable: 0, issingle: 0, is_virtual: 0 },
        });
    }

    const profile = grid.get_field("print_profile");
    if (profile) {
        profile.df.options = "Q Universal";
        profile.df.default = "Q Universal";
        profile.df.read_only = 1;
    }
}
