// ============================================================
// Employee - New Employee Announcement
// Editable TO and CC recipient lists
// DocType: Employee | Frappe 16
// ============================================================

frappe.ui.form.on("Employee", {
    refresh(frm) {
        employee_setup_announcement_button(frm);
    },

    status(frm) {
        employee_setup_announcement_button(frm);
    },

    date_of_joining(frm) {
        employee_setup_announcement_button(frm);
    },

    gender(frm) {
        employee_setup_announcement_button(frm);
    }
});

function employee_setup_announcement_button(frm) {
    frm.remove_custom_button(
        __("Send New Employee Announcement"),
        __("Actions")
    );

    if (frm.is_new()) {
        return;
    }

    const has_hr_permission =
        frappe.session.user === "Administrator" ||
        frappe.user.has_role("HR User") ||
        frappe.user.has_role("HR Manager");

    if (!has_hr_permission || frm.doc.status !== "Active") {
        return;
    }

    if (!frm.doc.date_of_joining || !frm.doc.gender) {
        return;
    }

    const normalized_gender = String(
        frm.doc.gender || ""
    ).trim().toLowerCase();

    if (![
        "male",
        "female",
        "ذكر",
        "أنثى",
        "انثى"
    ].includes(normalized_gender)) {
        return;
    }

    const new_employee_email =
        frm.doc.prefered_email ||
        frm.doc.company_email ||
        frm.doc.personal_email ||
        frm.doc.user_id ||
        "";

    if (!new_employee_email) {
        return;
    }

    const current_joining_date = String(
        frm.doc.date_of_joining || ""
    );

    const sent_for_joining_date = String(
        frm.doc.custom_welcome_email_sent_for_joining_date || ""
    );

    if (
        sent_for_joining_date &&
        sent_for_joining_date === current_joining_date
    ) {
        return;
    }

    frm.add_custom_button(
        __("Send New Employee Announcement"),
        () => employee_open_announcement_dialog(frm),
        __("Actions")
    );
}

async function employee_open_announcement_dialog(frm) {
    if (frm.is_dirty()) {
        frappe.throw(
            __("Please save the Employee record before sending the announcement.")
        );
    }

    frappe.dom.freeze(__("Loading recipient list..."));

    let preview;

    try {
        preview = await frappe.xcall(
            "qfap_adds.qfap_adds.api.employee_announcement.send_new_employee_announcement",
            {
                action: "preview",
                employee: frm.doc.name
            }
        );
    } catch (error) {
        frappe.msgprint({
            title: __("Recipients Could Not Be Loaded"),
            message: employee_announcement_error(error),
            indicator: "red"
        });
        return;
    } finally {
        frappe.dom.unfreeze();
    }

    if (!preview?.success) {
        frappe.throw(
            __("The server did not return the announcement recipient list.")
        );
    }

    const recipients_text = (
        preview.recipients || []
    ).join("\n");

    const cc_text = (
        preview.cc || []
    ).join("\n");

    const dialog = new frappe.ui.Dialog({
        title: __("Send New Employee Announcement"),
        size: "large",

        fields: [
            {
                fieldname: "employee_name",
                label: __("New Employee"),
                fieldtype: "Data",
                default: frm.doc.employee_name || frm.doc.name,
                read_only: 1
            },
            {
                fieldname: "joining_date",
                label: __("Date of Joining"),
                fieldtype: "Date",
                default: frm.doc.date_of_joining,
                read_only: 1
            },
            {
                fieldname: "mail_settings_section",
                fieldtype: "Section Break",
                label: __("Sender and Replies")
            },
            {
                fieldname: "sender_email",
                label: __("From"),
                fieldtype: "Data",
                options: "Email",
                default: preview.sender_email || "",
                read_only: 1,
                description: __(
                    "The current user's enabled outgoing Email Account is used when available; otherwise the system default outgoing account is used."
                )
            },
            {
                fieldname: "reply_to",
                label: __("Reply-To"),
                fieldtype: "Data",
                options: "Email",
                reqd: 1,
                default: preview.suggested_reply_to || preview.sender_email || "",
                description: __(
                    "Replies will be directed to this address. You may change it before sending."
                )
            },
            {
                fieldname: "recipients_section",
                fieldtype: "Section Break",
                label: __("Email Recipients")
            },
            {
                fieldname: "recipients",
                label: __("To"),
                fieldtype: "Small Text",
                reqd: 1,
                default: recipients_text,
                description: __(
                    "One email per line. You may add or remove recipients. Commas and semicolons are also accepted."
                )
            },
            {
                fieldname: "cc",
                label: __("CC"),
                fieldtype: "Small Text",
                default: cc_text,
                description: __(
                    "The new employee is included in CC by default. You may add or remove addresses. Enter one email per line; commas and semicolons are also accepted."
                )
            },
            {
                fieldname: "recipient_summary",
                fieldtype: "HTML",
                options:
                    "<div class='alert alert-info' style='margin-top:8px;'>" +
                    __(
                        "The default list contains {0} team member(s) in TO and {1} address(es) in CC. The new employee is included in CC by default. Review both lists before sending.",
                        [
                            preview.recipient_count || 0,
                            preview.cc_count || 0
                        ]
                    ) +
                    "</div>"
            },
            {
                fieldname: "message_section",
                fieldtype: "Section Break",
                label: __("Message")
            },
            {
                fieldname: "additional_message",
                label: __("Additional Message"),
                fieldtype: "Small Text",
                description: __(
                    "Optional message to include in the bilingual announcement."
                )
            }
        ],

        primary_action_label: __("Send Announcement"),

        primary_action: async values => {
            const to_list = employee_parse_emails(values.recipients);
            const cc_list = employee_parse_emails(values.cc);
            const reply_to = String(values.reply_to || "").trim();

            if (!reply_to || !employee_is_valid_email(reply_to)) {
                frappe.msgprint({
                    title: __("Valid Reply-To Required"),
                    message: __("Enter one valid Reply-To email address."),
                    indicator: "orange"
                });
                return;
            }

            if (!to_list.length) {
                frappe.msgprint({
                    title: __("Recipients Required"),
                    message: __("Add at least one email address in the TO field."),
                    indicator: "orange"
                });
                return;
            }

            const invalid_emails = [
                ...to_list,
                ...cc_list
            ].filter(email => !employee_is_valid_email(email));

            if (invalid_emails.length) {
                frappe.msgprint({
                    title: __("Invalid Email Address"),
                    message: __(
                        "Please correct the following email addresses:<br>{0}",
                        [invalid_emails.join("<br>")]
                    ),
                    indicator: "red"
                });
                return;
            }

            const confirmed = await new Promise(resolve => {
                frappe.confirm(
                    __(
                        "Send this announcement to {0} TO recipient(s) and {1} CC recipient(s)?",
                        [to_list.length, cc_list.length]
                    ),
                    () => resolve(true),
                    () => resolve(false)
                );
            });

            if (!confirmed) {
                return;
            }

            dialog.disable_primary_action();
            frappe.dom.freeze(__("Queueing new employee announcement..."));

            try {
                const result = await frappe.xcall(
                    "qfap_adds.qfap_adds.api.employee_announcement.send_new_employee_announcement",
                    {
                        action: "send",
                        employee: frm.doc.name,
                        recipients: to_list.join("\n"),
                        cc: cc_list.join("\n"),
                        reply_to,
                        additional_message:
                            values.additional_message || ""
                    }
                );

                if (!result?.success) {
                    frappe.throw(
                        __("The server did not confirm that the announcement was queued.")
                    );
                }

                dialog.hide();

                frappe.show_alert({
                    message: __(
                        "Announcement queued from {0} for {1} TO recipient(s) and {2} CC recipient(s). Replies will go to {3}.",
                        [
                            result.sender_email,
                            result.recipient_count,
                            result.cc_count,
                            result.reply_to
                        ]
                    ),
                    indicator: "green"
                });

                await frm.reload_doc();

            } catch (error) {
                console.error(
                    "Unable to send new employee announcement",
                    error
                );

                frappe.msgprint({
                    title: __("Announcement Could Not Be Sent"),
                    message: employee_announcement_error(error),
                    indicator: "red"
                });

                dialog.enable_primary_action();

            } finally {
                frappe.dom.unfreeze();
            }
        }
    });

    dialog.show();
}

function employee_parse_emails(raw_value) {
    const entries = String(raw_value || "")
        .replace(/;/g, ",")
        .replace(/\n/g, ",")
        .split(",")
        .map(value => value.trim())
        .filter(Boolean);

    const result = [];
    const keys = new Set();

    entries.forEach(email => {
        const key = email.toLowerCase();

        if (!keys.has(key)) {
            keys.add(key);
            result.push(email);
        }
    });

    return result;
}

function employee_is_valid_email(email) {
    const value = String(email || "").trim();

    if (!value || value.includes(" ")) {
        return false;
    }

    const parts = value.split("@");

    if (parts.length !== 2 || !parts[0] || !parts[1]) {
        return false;
    }

    const domain = parts[1];

    return (
        domain.includes(".") &&
        !domain.startsWith(".") &&
        !domain.endsWith(".") &&
        !value.includes("..")
    );
}

function employee_announcement_error(error) {
    let message = "";

    try {
        const server_messages = JSON.parse(
            error?._server_messages || "[]"
        );

        message = server_messages
            .map(item => {
                try {
                    return JSON.parse(item).message;
                } catch {
                    return item;
                }
            })
            .filter(Boolean)
            .join("<br>");
    } catch {
        message = "";
    }

    return (
        message ||
        error?.message ||
        __("The announcement could not be sent. Please review the employee data and try again.")
    );
}

