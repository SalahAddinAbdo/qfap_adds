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
    if (!grid) return;

    const documentType = grid.get_field("document_type");
    if (documentType) {
        documentType.get_query = () => ({
            filters: {
                istable: 0,
                issingle: 0,
                is_virtual: 0,
            },
        });
    }

    const profile = grid.get_field("print_profile");
    if (profile) {
        profile.df.options = "Q Universal";
        profile.df.default = "Q Universal";
        profile.df.read_only = 1;
    }

    const widths = {
        document_type: 3,
        enabled: 1,
        print_profile: 2,
        set_as_default: 1,
        include_letter_head: 1,
        include_workflow_status: 1,
        include_signatures: 1,
    };
    Object.entries(widths).forEach(([fieldname, columns]) => {
        const field = grid.get_field(fieldname);
        if (field) {
            field.df.in_list_view = 1;
            field.df.columns = columns;
        }
    });

    ["include_audit_information", "include_attachments"].forEach((fieldname) => {
        const field = grid.get_field(fieldname);
        if (field) field.df.in_list_view = 0;
    });

    grid.refresh();
}
