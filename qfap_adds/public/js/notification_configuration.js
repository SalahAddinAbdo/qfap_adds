frappe.ui.form.on("Notification", {
    refresh(frm) {
        load_notification_user_fields(frm);
    },

    document_type(frm) {
        load_notification_user_fields(frm);
    },

    channel(frm) {
        load_notification_user_fields(frm);
    }
});

function load_notification_user_fields(frm) {
    if (
        !frm.doc.document_type ||
        frm.doc.channel !== "System Notification"
    ) {
        return;
    }

    frappe.model.with_doctype(frm.doc.document_type, () => {
        const meta = frappe.get_meta(frm.doc.document_type);
        const grid = frm.fields_dict.recipients?.grid;

        if (!meta || !grid) return;

        const options = ["", "owner"];

        meta.fields.forEach(df => {
            const is_user_field =
                df.fieldtype === "Link" &&
                df.options === "User";

            const is_email_field =
                df.fieldtype === "Data" &&
                df.options === "Email";

            if (
                (is_user_field || is_email_field) &&
                !options.includes(df.fieldname)
            ) {
                options.push(df.fieldname);
            }
        });

        // Preserve fields already entered in recipient rows.
        (frm.doc.recipients || []).forEach(row => {
            const value = row.receiver_by_document_field;

            if (value && !options.includes(value)) {
                options.push(value);
            }
        });

        grid.update_docfield_property(
            "receiver_by_document_field",
            "options",
            options.join("\n")
        );

        frm.refresh_field("recipients");

        console.log(
            "Loaded Notification recipient fields:",
            options
        );
    });
}
