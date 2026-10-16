// ============================================================
// Unified Workflow Handler for Frappe 16
// Change only the DocType name when copying this script.
// ============================================================
window.qfap_initialize_document_workflow = function (frm) {
    frm = frm || window.cur_frm;
    if (!frm || frm.__qfap_workflow_handler_registered) return;
    frm.__qfap_workflow_handler_registered = true;

    frappe.ui.form.on(frm.doctype, {
        setup(current) {
            wf_restrict_employee_signatures(current);
        },
        onload(current) {
            wf_prepare_new_document(current);
        },
        refresh(current) {
            wf_restrict_employee_signatures(current);
            if (current.is_new() || !wf_protect_document(current)) return;
            setTimeout(() => wf_setup(current), 500);
        }
    });

    wf_restrict_employee_signatures(frm);
    wf_prepare_new_document(frm);
    if (!frm.is_new() && wf_protect_document(frm)) {
        setTimeout(() => wf_setup(frm), 150);
    }
};

window.qfap_initialize_document_workflow(window.cur_frm);

// Clear responsibility copied from a source document. The server repeats this
// protection for imports and API-created documents.
function wf_prepare_new_document(frm) {
    if (!frm.is_new() || frm.__wf_new_document_prepared) return;
    const workflow = frappe.workflow?.workflows?.[frm.doctype];
    const fields = new Set(["custom_current_responsible_user"]);
    (workflow?.transitions || []).forEach(transition => {
        const fieldname = String(transition.custom_target_user_field || "").trim();
        if (fieldname) fields.add(fieldname);
    });
    fields.forEach(fieldname => {
        if (frm.fields_dict?.[fieldname] && frm.doc[fieldname]) {
            frappe.model.set_value(frm.doc.doctype, frm.doc.name, fieldname, "");
        }
    });
    frm.__wf_new_document_prepared = true;
}

// Restrict every visible/editable Employee Signature link to the session user.
function wf_restrict_employee_signatures(frm) {
    if (frappe.session.user === "Administrator") return;

    (frm.meta?.fields || [])
        .filter(df =>
            df.fieldname &&
            df.fieldtype === "Link" &&
            df.options === "Employee Signature"
        )
        .forEach(df => {
            frm.set_query(df.fieldname, () => ({
                filters: { user_id: frappe.session.user }
            }));
        });
}

async function wf_setup(frm) {
    if (frm.__wf_setup_running || frm.__wf_processing) return;

    const workflow = frappe.workflow?.workflows?.[frm.doctype];
    if (!workflow?.transitions?.length) return;

    frm.__wf_setup_running = true;
    try {
        let allowed = [];
        try {
            allowed = await frappe.xcall(
                "frappe.model.workflow.get_transitions",
                { doc: frm.doc }
            );
        } catch (error) {
            console.error("Unable to load workflow transitions", error);
            frappe.show_alert({
                message: __("Workflow actions could not be loaded. Please refresh the page."),
                indicator: "orange"
            });
            return;
        }

        const allowed_actions = new Set(
            (allowed || []).map(row => wf_normalize(row.action))
        );
        const processed = new Set();

        workflow.transitions.forEach(transition => {
            const action = String(transition.action || "").trim();
            const key = wf_normalize(action);
            const state_matches =
                wf_normalize(transition.state) ===
                wf_normalize(frm.doc.workflow_state);

            if (!action || !state_matches || !allowed_actions.has(key) || processed.has(key)) return;

            processed.add(key);
            wf_hide_standard_action(frm, action);
            frm.remove_custom_button(__(action), __("Actions"));
            frm.add_custom_button(
                __(action),
                () => wf_open_action_dialog(frm, transition),
                __("Actions")
            );
        });

        wf_style_actions(frm);
    } finally {
        frm.__wf_setup_running = false;
    }
}

async function wf_open_action_dialog(frm, transition) {
    if (frm.__wf_processing) {
        frappe.show_alert({
            message: __("A workflow action is already being processed. Please wait."),
            indicator: "orange"
        });
        return;
    }

    const assignment_required = wf_checked(transition.custom_assignment_required);
    const apply_signature = wf_checked(transition.custom_apply_employee_signature);
    const target_field = String(transition.custom_target_user_field || "").trim();
    const target_role = String(transition.custom_target_role || "").trim();
    const show_user = assignment_required || Boolean(target_field);
    const signature_context = apply_signature
        ? await wf_get_signature_dialog_context(frm, transition)
        : { include_signature_notes: false, signature_notes: "" };

    if (show_user && !target_field) {
        return wf_message(
            __("Incomplete Workflow Configuration"),
            __("Action {0} requires assignment, but Target User Field is not configured.", [transition.action || ""])
        );
    }
    if (show_user && !frm.fields_dict?.[target_field]) {
        return wf_message(
            __("Invalid Workflow Configuration"),
            __("Field {0} does not exist in {1}.", [target_field, frm.doctype])
        );
    }

    const fields = [];
    if (show_user) {
        fields.push({
            fieldname: "user",
            label: __("Next Responsible User"),
            fieldtype: "Link",
            options: "User",
            reqd: assignment_required ? 1 : 0,
            description: target_role
                ? __("Select an enabled user with role") + " " + __(target_role) + "."
                : __("Select the user responsible for the next stage."),
            get_query() {
                const filters = { enabled: 1 };
                if (target_role) filters.role = target_role;
                return {
                    query: "frappe.core.doctype.user.user.user_query",
                    filters
                };
            }
        });
    }

    if (apply_signature && signature_context.include_signature_notes) {
        fields.push({
            fieldname: "signature_notes",
            label: __("Signature Notes"),
            fieldtype: "Small Text",
            reqd: 0,
            default: signature_context.signature_notes || "",
            description: __("Optional. The previously saved note is shown here and may be retained or updated.")
        });
    }

    fields.push({
        fieldname: "workflow_comment",
        label: __("Internal Comment"),
        fieldtype: "Small Text",
        reqd: 0,
        description: __("Optional. The comment will be recorded after the workflow action succeeds.")
    });

    const dialog = new frappe.ui.Dialog({
        title: __(transition.custom_workflow_prompt || transition.action || "Workflow Action"),
        fields,
        primary_action_label: show_user ? __("Assign & Continue") : __("Continue"),
        primary_action: async values => {
            const selected_user = String(values?.user || "").trim();
            const signature_notes = String(values?.signature_notes || "").trim();
            const comment = String(values?.workflow_comment || "").trim();

            if (assignment_required && !selected_user) {
                frappe.show_alert({
                    message: __("Please select the next responsible user."),
                    indicator: "orange"
                });
                return;
            }

            dialog.disable_primary_action();
            const completed = await wf_run_transition(
                frm,
                transition,
                selected_user,
                signature_notes,
                comment
            );
            if (completed) dialog.hide();
            else dialog.enable_primary_action();
        }
    });

    dialog.show();
    setTimeout(() => {
        dialog.fields_dict?.[
            show_user
                ? "user"
                : (apply_signature && signature_context.include_signature_notes
                    ? "signature_notes"
                    : "workflow_comment")
        ]?.set_focus?.();
    }, 150);
}

async function wf_get_signature_dialog_context(frm, transition) {
    const mapping_key = String(
        transition.custom_employee_signature_mapping_key || ""
    ).trim();
    if (!mapping_key || frm.is_new() || !frm.doc.name) {
        return { include_signature_notes: false, signature_notes: "" };
    }
    try {
        const result = await frappe.xcall(
            "qfap_adds.qfap_adds.api.signatures.get_signature_dialog_context",
            {
                doctype: frm.doc.doctype,
                document_name: frm.doc.name,
                mapping_key
            }
        );
        return {
            include_signature_notes: wf_checked(result?.include_signature_notes),
            signature_notes: String(result?.signature_notes || "")
        };
    } catch (error) {
        console.error("Unable to load signature dialog context", error);
        wf_show_error(error);
        return { include_signature_notes: false, signature_notes: "" };
    }
}

async function wf_run_transition(frm, transition, selected_user = "", signature_notes = "", comment = "") {
    if (frm.__wf_processing) return false;

    frm.__wf_processing = true;
    frappe.dom.freeze(__("Processing workflow action..."));

    const target_field = String(transition.custom_target_user_field || "").trim();
    const previous_target = target_field ? frm.doc[target_field] || "" : "";
    const previous_responsible = frm.doc.custom_current_responsible_user || "";
    let workflow_completed = false;

    try {
        if (frm.is_dirty()) {
            frappe.throw(__("The document contains unsaved changes. Please save it before continuing."));
        }

        await wf_apply_signature(frm, transition, signature_notes);
        if (selected_user) await wf_set_responsible(frm, transition, selected_user);
        await wf_apply_action(frm, transition.action);
        workflow_completed = true;

        const comment_saved = await wf_add_comment(frm, comment);
        frappe.show_alert({
            message: comment && !comment_saved
                ? __("The workflow action succeeded, but the comment could not be recorded.")
                : comment
                    ? __("Workflow action {0} completed and the comment was recorded.", [transition.action || ""])
                    : __("Workflow action {0} completed successfully.", [transition.action || ""]),
            indicator: comment && !comment_saved ? "orange" : "green"
        });
        return true;
    } catch (error) {
        console.error("Workflow action failed", error);
        if (selected_user && !workflow_completed) {
            await wf_restore_responsibility(
                frm,
                target_field,
                previous_target,
                previous_responsible
            );
        }
        wf_show_error(error);
        return false;
    } finally {
        frappe.dom.unfreeze();
        frm.__wf_processing = false;
    }
}

async function wf_apply_signature(frm, transition, signature_notes = "") {
    if (!wf_checked(transition.custom_apply_employee_signature)) return;

    const mapping_key = String(
        transition.custom_employee_signature_mapping_key || ""
    ).trim();
    if (!mapping_key) {
        frappe.throw(__("Employee Signature Mapping is missing for action {0}.", [transition.action || ""]));
    }

    const result = await frappe.xcall("qfap_adds.qfap_adds.api.signatures.apply_current_employee_signature", {
        doctype: frm.doc.doctype,
        document_name: frm.doc.name,
        mapping_key,
        signature_notes
    });
    if (!result) frappe.throw(__("The employee signature service returned no response."));

    if (wf_checked(result.signed)) {
        await frm.reload_doc();
        frappe.show_alert({
            message: wf_checked(result.already_signed)
                ? __("Your signature was already recorded for this stage.")
                : __("Your employee signature was applied successfully."),
            indicator: wf_checked(result.already_signed) ? "blue" : "green"
        });
        return;
    }

    frappe.show_alert({
        message: __("No signature was applied because no active signature exists and the configured signature is optional."),
        indicator: "orange"
    });
}

async function wf_set_responsible(frm, transition, user) {
    const target_field = String(transition.custom_target_user_field || "").trim();
    if (!user) frappe.throw(__("The next responsible user is required."));
    if (!target_field) {
        frappe.throw(__("Target User Field is not configured for action {0}.", [transition.action || ""]));
    }
    if (!frm.fields_dict?.[target_field]) {
        frappe.throw(__("Target User Field {0} does not exist in {1}.", [target_field, frm.doctype]));
    }

    if (frm.doc[target_field] !== user) await frm.set_value(target_field, user);
    if (
        frm.fields_dict?.custom_current_responsible_user &&
        frm.doc.custom_current_responsible_user !== user
    ) {
        await frm.set_value("custom_current_responsible_user", user);
    }
    if (frm.is_dirty()) await frm.save();
}

async function wf_restore_responsibility(frm, target_field, previous_target, previous_responsible) {
    try {
        if (target_field && frm.fields_dict?.[target_field]) {
            await frm.set_value(target_field, previous_target);
        }
        if (frm.fields_dict?.custom_current_responsible_user) {
            await frm.set_value("custom_current_responsible_user", previous_responsible);
        }
        if (frm.is_dirty()) await frm.save();
    } catch (error) {
        console.error("Unable to restore previous responsible user", error);
        frappe.show_alert({
            message: __("The workflow failed, and the previous responsible user could not be restored automatically."),
            indicator: "red"
        });
    }
}

async function wf_apply_action(frm, action) {
    if (!action) frappe.throw(__("The workflow action is missing."));

    const updated_doc = await frappe.xcall(
        "frappe.model.workflow.apply_workflow",
        { doc: frm.doc, action }
    );
    if (updated_doc) frappe.model.sync(updated_doc);
    await frm.reload_doc();
}

async function wf_add_comment(frm, text) {
    const content = String(text || "").trim();
    if (!content) return true;

    try {
        await frappe.call({
            method: "frappe.desk.form.utils.add_comment",
            args: {
                reference_doctype: frm.doc.doctype,
                reference_name: frm.doc.name,
                content,
                comment_email: frappe.session.user,
                comment_by: frappe.session.user_fullname || frappe.session.user
            },
            freeze: false
        });

        try {
            if (frm.timeline?.refresh) await frm.timeline.refresh();
            else await frm.reload_doc();
        } catch (error) {
            console.warn("Comment saved, but timeline refresh failed", error);
        }
        return true;
    } catch (error) {
        console.error("Unable to add workflow comment", error);
        return false;
    }
}

function wf_protect_document(frm) {
    const responsible = String(
        frm.doc.custom_current_responsible_user || ""
    ).trim();
    if (!responsible) {
        wf_unlock_document_fields(frm);
        return true;
    }
    const can_override =
        frappe.session.user === "Administrator" ||
        frappe.user.has_role("Workflow Admin") ||
        frappe.user.has_role("System Manager");
    const is_responsible =
        wf_normalize(frappe.session.user) === wf_normalize(responsible);
    if (is_responsible || can_override) {
        wf_unlock_document_fields(frm);
        return true;
    }

    // Lock document data only. Do not call disable_form(), clear_menu(), or
    // clear_actions_menu(), because ERPNext places permitted related-document
    // actions such as Request for Quotation and Purchase Order in those menus.
    wf_lock_document_fields(frm);
    wf_hide_workflow_actions_only(frm);

    if (!frm.__wf_responsibility_alert_shown) {
        frm.__wf_responsibility_alert_shown = true;
        frappe.show_alert({
            message: __("This document is assigned to {0}. You may read it and use permitted standard actions, but only the responsible user can edit it or perform workflow actions.", [responsible]),
            indicator: "orange"
        });
    }
    return false;
}

function wf_lock_document_fields(frm) {
    if (frm.__wf_fields_locked) return;
    frm.__wf_original_field_state = {};
    (frm.meta?.fields || []).forEach(df => {
        const control = frm.fields_dict?.[df.fieldname];
        if (!df.fieldname || !control || [
            "Section Break", "Column Break", "Tab Break", "HTML",
            "Button", "Heading", "Fold"
        ].includes(df.fieldtype)) return;
        frm.__wf_original_field_state[df.fieldname] = {
            read_only: Boolean(df.read_only),
            cannot_add_rows: control.grid?.cannot_add_rows ?? null,
            cannot_delete_rows: control.grid?.cannot_delete_rows ?? null
        };
        frm.set_df_property(df.fieldname, "read_only", 1);
        if (control.grid) {
            control.grid.cannot_add_rows = true;
            control.grid.cannot_delete_rows = true;
            control.grid.wrapper
                .find(".grid-add-row,.grid-remove-rows,.grid-delete-row")
                .hide();
        }
    });
    frm.__wf_fields_locked = true;
    frm.refresh_fields();
}

function wf_unlock_document_fields(frm) {
    if (!frm.__wf_fields_locked) return;
    Object.entries(frm.__wf_original_field_state || {}).forEach(([fieldname, state]) => {
        const control = frm.fields_dict?.[fieldname];
        if (!control) return;
        frm.set_df_property(fieldname, "read_only", state.read_only ? 1 : 0);
        if (control.grid) {
            if (state.cannot_add_rows !== null) {
                control.grid.cannot_add_rows = state.cannot_add_rows;
            }
            if (state.cannot_delete_rows !== null) {
                control.grid.cannot_delete_rows = state.cannot_delete_rows;
            }
            if (!state.cannot_add_rows) control.grid.wrapper.find(".grid-add-row").show();
            if (!state.cannot_delete_rows) {
                control.grid.wrapper.find(".grid-remove-rows,.grid-delete-row").show();
            }
        }
    });
    frm.__wf_fields_locked = false;
    frm.refresh_fields();
}

function wf_current_transition_labels(frm) {
    const workflow = frappe.workflow?.workflows?.[frm.doctype];
    const state = wf_normalize(frm.doc.workflow_state);
    return new Set(
        (workflow?.transitions || [])
            .filter(row => wf_normalize(row.state) === state)
            .flatMap(row => [wf_normalize(row.action), wf_normalize(__(row.action || ""))])
            .filter(Boolean)
    );
}

function wf_hide_workflow_actions_only(frm) {
    const labels = wf_current_transition_labels(frm);
    if (!labels.size) return;
    const hide = () => {
        const wrapper = $(frm.page?.wrapper || frm.wrapper);
        // Dedicated workflow controls may be hidden as a group.
        wrapper.find(".workflow-button-group").hide();
        // In shared Actions menus, hide only entries whose label is a current
        // workflow transition. Preserve Create and all standard ERPNext actions.
        wrapper.find(".custom-actions li, .custom-actions .dropdown-item, .actions-btn-group li").each(function () {
            const item = $(this);
            const control = item.find("a,button").first();
            const candidates = [
                item.attr("data-label"), control.attr("data-label"),
                control.text(), item.clone().children().remove().end().text(), item.text()
            ].map(wf_normalize).filter(Boolean);
            if (candidates.some(label => labels.has(label))) item.hide();
        });
    };
    hide();
    [200, 500, 1000].forEach(delay => setTimeout(hide, delay));
}

function wf_hide_standard_action(frm, action) {
    const labels = new Set([wf_normalize(action), wf_normalize(__(action))]);
    const hide = () => {
        frm.page?.actions?.find("li").each(function () {
            const $item = $(this);
            const $control = $item.find("a,button").first();
            const values = [
                $item.text(),
                $item.attr("data-label"),
                $control.text(),
                $control.attr("data-label")
            ];
            if (values.some(value => value && labels.has(wf_normalize(value)))) {
                $item.hide();
            }
        });
    };
    hide();
    [200, 500, 1000].forEach(delay => setTimeout(hide, delay));
}

function wf_style_actions(frm) {
    const apply = () => {
        $(frm.page?.wrapper || frm.wrapper)
            .find(".custom-actions .inner-group-button > button")
            .filter(function () {
                return wf_normalize($(this).text()) === wf_normalize(__("Actions"));
            })
            .removeClass("btn-default")
            .addClass("btn-primary")
            .css({ color: "#fff" });
    };
    apply();
    [200, 500, 1000].forEach(delay => setTimeout(apply, delay));
}

function wf_show_error(error) {
    let message = "";
    try {
        message = JSON.parse(error?._server_messages || "[]")
            .map(item => {
                try { return JSON.parse(item).message; }
                catch { return item; }
            })
            .filter(Boolean)
            .join("<br>");
    } catch {
        message = "";
    }

    frappe.msgprint({
        title: __("Workflow Action Failed"),
        message: message || error?.message || __("The workflow action could not be completed. Please review the document and try again."),
        indicator: "red"
    });
}

function wf_message(title, message) {
    frappe.msgprint({ title, message, indicator: "red" });
}

function wf_checked(value) {
    return value === true || value === 1 || String(value || "") === "1";
}

function wf_normalize(value) {
    return String(value ?? "")
        .replace(/\u00A0/g, " ")
        .replace(/[\u200B-\u200F\u202A-\u202E\u2060\uFEFF]/g, "")
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase();
}

