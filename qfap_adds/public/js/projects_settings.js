(function () {
    function enable_notification_rules_grid(frm) {
        const field = frm.fields_dict.project_notification_rules;
        if (!field || !field.grid) return;

        frm.set_df_property("project_notification_rules", "read_only", 0);
        const grid = field.grid;
        grid.df.read_only = 0;
        grid.cannot_add_rows = false;
        grid.cannot_delete_rows = false;
        grid.only_sortable = false;

        [
            "delivery_channel",
            "enabled",
            "due_soon_days",
            "recipient_role",
            "recipient_users",
            "recipient_employees",
            "fallback_to_project_manager",
        ].forEach((fieldname) => {
            grid.update_docfield_property(fieldname, "read_only", 0);
        });

        [
            "notification_key",
            "rule_label",
            "description",
            "reference_doctype",
            "trigger_type",
            "notification_record",
        ].forEach((fieldname) => {
            grid.update_docfield_property(fieldname, "read_only", 1);
        });

        grid.refresh();
    }

    frappe.ui.form.on("Projects Settings", {
        setup(frm) {
            enable_notification_rules_grid(frm);
        },
        onload_post_render(frm) {
            enable_notification_rules_grid(frm);
        },
        refresh(frm) {
            enable_notification_rules_grid(frm);
        },
    });
})();
