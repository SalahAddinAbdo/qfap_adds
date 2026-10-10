// ============================================================
// Workflow Dynamic Configuration
// 1. Loads User Link fields for workflow assignment.
// 2. Loads Employee Signature Mapping Keys for signatures.
// ============================================================

frappe.ui.form.on("Workflow", {
    async refresh(frm) {
        await workflow_load_dynamic_options(frm);
    },

    async document_type(frm) {
        await workflow_handle_document_type_change(frm);
    },

    validate(frm) {
        workflow_validate_transition_settings(frm);
    }
});


frappe.ui.form.on("Workflow Transition", {
    custom_assignment_required(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "custom_target_user_field", row.custom_assignment_required ? "custom_current_responsible_user" : "");
    },
    custom_apply_employee_signature(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        if (!row.custom_apply_employee_signature) {
            frappe.model.set_value(
                cdt,
                cdn,
                "custom_employee_signature_mapping_key",
                ""
            );
        }
    }
});


// ============================================================
// Main Loader
// ============================================================

async function workflow_load_dynamic_options(frm) {
    if (!frm.doc.document_type) {
        workflow_clear_dynamic_options(frm);
        return;
    }

    await Promise.all([
        workflow_load_user_fields(frm),
        workflow_load_signature_mappings(frm)
    ]);

    frm.refresh_field("transitions");
}


// ============================================================
// Handle Document Type Change
// ============================================================

async function workflow_handle_document_type_change(frm) {
    workflow_clear_invalid_transition_values(frm);

    await workflow_load_dynamic_options(frm);
}


// ============================================================
// Load User Link Fields
// ============================================================

async function workflow_load_user_fields(frm) {
    const document_type = frm.doc.document_type;

    if (!document_type) {
        workflow_set_grid_options(
            frm,
            "custom_target_user_field",
            [""]
        );

        return;
    }

    try {
        await frappe.model.with_doctype(
            document_type
        );

        const meta = frappe.get_meta(
            document_type
        );

        const user_fields = [""];

        (meta.fields || []).forEach(function (df) {
            if (
                df.fieldname &&
                df.fieldtype === "Link" &&
                df.options === "User" &&
                !df.hidden
            ) {
                user_fields.push(
                    df.fieldname
                );
            }
        });

        user_fields.sort(
            workflow_sort_empty_first
        );

        workflow_set_grid_options(
            frm,
            "custom_target_user_field",
            user_fields
        );

        workflow_clear_invalid_user_fields(
            frm,
            user_fields
        );

    } catch (error) {
        console.error(
            "Failed to load User fields",
            error
        );

        workflow_set_grid_options(
            frm,
            "custom_target_user_field",
            [""]
        );

        frappe.msgprint({
            title: __("Workflow Configuration"),
            message: __(
                "The User fields could not be loaded from the selected Document Type."
            ),
            indicator: "red"
        });
    }
}


// ============================================================
// Load Signature Mapping Keys
// ============================================================

async function workflow_load_signature_mappings(frm) {
    const document_type = frm.doc.document_type;

    if (!document_type) {
        workflow_set_grid_options(
            frm,
            "custom_employee_signature_mapping_key",
            [""]
        );

        return;
    }

    try {
        const configuration_result =
            await frappe.db.get_value(
                "Employee Signature Configuration",
                {
                    document_type: document_type,
                    enabled: 1
                },
                [
                    "name",
                    "configuration_name"
                ]
            );

        const configuration =
            configuration_result.message || {};

        if (!configuration.name) {
            workflow_set_grid_options(
                frm,
                "custom_employee_signature_mapping_key",
                [""]
            );

            workflow_clear_invalid_signature_mappings(
                frm,
                []
            );

            return;
        }

        const configuration_doc =
            await frappe.db.get_doc(
                "Employee Signature Configuration",
                configuration.name
            );

        const mapping_keys = [""];

        (
            configuration_doc.signature_mappings || []
        ).forEach(function (row) {
            if (
                row.enabled &&
                row.mapping_key &&
                row.employee_signature_field
            ) {
                mapping_keys.push(
                    row.mapping_key
                );
            }
        });

        const unique_mapping_keys = [
            ...new Set(mapping_keys)
        ];

        unique_mapping_keys.sort(
            workflow_sort_empty_first
        );

        workflow_set_grid_options(
            frm,
            "custom_employee_signature_mapping_key",
            unique_mapping_keys
        );

        workflow_clear_invalid_signature_mappings(
            frm,
            unique_mapping_keys
        );

    } catch (error) {
        console.error(
            "Failed to load Employee Signature mappings",
            error
        );

        workflow_set_grid_options(
            frm,
            "custom_employee_signature_mapping_key",
            [""]
        );

        frappe.msgprint({
            title: __("Workflow Configuration"),
            message: __(
                "The Employee Signature mappings could not be loaded for the selected Document Type."
            ),
            indicator: "red"
        });
    }
}


// ============================================================
// Set Child Table Select Options
// ============================================================

function workflow_set_grid_options(
    frm,
    fieldname,
    options
) {
    const grid =
        frm.fields_dict.transitions &&
        frm.fields_dict.transitions.grid;

    if (!grid) {
        return;
    }

    grid.update_docfield_property(
        fieldname,
        "options",
        (options || [""]).join("\n")
    );
}


// ============================================================
// Clear Invalid Values after Document Type Change
// ============================================================

function workflow_clear_invalid_transition_values(frm) {
    (frm.doc.transitions || []).forEach(
        function (row) {
            frappe.model.set_value(
                row.doctype,
                row.name,
                "custom_target_user_field",
                ""
            );

            frappe.model.set_value(
                row.doctype,
                row.name,
                "custom_employee_signature_mapping_key",
                ""
            );
        }
    );
}


function workflow_clear_invalid_user_fields(
    frm,
    valid_options
) {
    const valid = new Set(
        valid_options || []
    );

    (frm.doc.transitions || []).forEach(
        function (row) {
            const value =
                row.custom_target_user_field;

            if (
                value &&
                !valid.has(value)
            ) {
                frappe.model.set_value(
                    row.doctype,
                    row.name,
                    "custom_target_user_field",
                    ""
                );
            }
        }
    );
}


function workflow_clear_invalid_signature_mappings(
    frm,
    valid_options
) {
    const valid = new Set(
        valid_options || []
    );

    (frm.doc.transitions || []).forEach(
        function (row) {
            const value =
                row.custom_employee_signature_mapping_key;

            if (
                value &&
                !valid.has(value)
            ) {
                frappe.model.set_value(
                    row.doctype,
                    row.name,
                    "custom_employee_signature_mapping_key",
                    ""
                );
            }
        }
    );
}


// ============================================================
// Clear Options when no Document Type is selected
// ============================================================

function workflow_clear_dynamic_options(frm) {
    workflow_set_grid_options(
        frm,
        "custom_target_user_field",
        [""]
    );

    workflow_set_grid_options(
        frm,
        "custom_employee_signature_mapping_key",
        [""]
    );
}


// ============================================================
// Client-Side Validation
// ============================================================

function workflow_validate_transition_settings(frm) {
    const action_keys = new Set();

    (frm.doc.transitions || []).forEach(
        function (row, index) {
            const row_number = index + 1;

            const assignment_required = Boolean(Number(row.custom_assignment_required || 0));
            if (assignment_required) {
                row.custom_target_user_field = "custom_current_responsible_user";
                if (!row.custom_target_role) {
                    frappe.throw(__("Target Role is required in Workflow Transition row {0}.", [row_number]));
                }
                if (!row.custom_workflow_prompt) {
                    frappe.throw(__("Workflow Prompt is required in Workflow Transition row {0}.", [row_number]));
                }
            } else {
                row.custom_target_user_field = "";
            }

            const apply_signature =
                row.custom_apply_employee_signature === 1 ||
                row.custom_apply_employee_signature === true ||
                String(
                    row.custom_apply_employee_signature || ""
                ) === "1";

            if (
                apply_signature &&
                !row.custom_employee_signature_mapping_key
            ) {
                frappe.throw(
                    __(
                        "Employee Signature Mapping is required in Workflow Transition row {0}.",
                        [row_number]
                    )
                );
            }

            if (
                !apply_signature &&
                row.custom_employee_signature_mapping_key
            ) {
                frappe.throw(
                    __(
                        "Enable Apply Employee Signature before selecting a Signature Mapping in row {0}.",
                        [row_number]
                    )
                );
            }

            if (
                apply_signature &&
                row.custom_employee_signature_mapping_key
            ) {
                const transition_key = [
                    row.state || "",
                    row.action || "",
                    row.custom_employee_signature_mapping_key
                ].join("|");

                if (action_keys.has(transition_key)) {
                    frappe.throw(
                        __(
                            "The same Signature Mapping is duplicated for the same Workflow transition in row {0}.",
                            [row_number]
                        )
                    );
                }

                action_keys.add(
                    transition_key
                );
            }
        }
    );
}


// ============================================================
// Sorting Helper
// ============================================================

function workflow_sort_empty_first(a, b) {
    if (!a) return -1;
    if (!b) return 1;

    return String(a).localeCompare(
        String(b)
    );
}

