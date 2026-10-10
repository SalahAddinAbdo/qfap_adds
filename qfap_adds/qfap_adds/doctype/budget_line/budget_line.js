// Budget Line - Unified Client Script v2.0
// Frappe / ERPNext 16

const BUDGET_TOP_LEVEL_CODES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

frappe.ui.form.on("Budget Line", {
    setup(frm) {
        set_budget_line_queries(frm);
    },

    refresh(frm) {
        set_budget_line_queries(frm);
        apply_budget_line_controls(frm);
        load_budget_line_currency(frm);
        preview_budget_line_code(frm);
    },

    project(frm) {
        if (frm.doc.parent_budget_line) frm.set_value("parent_budget_line", "");
        if (!frm.doc.use_custom_code) frm.set_value("budget_line", "");
        set_budget_line_queries(frm);
        load_budget_line_currency(frm, true);
        preview_budget_line_code(frm);
    },

    parent_budget_line(frm) {
        load_parent_budget_line(frm).then(() => preview_budget_line_code(frm));
    },

    is_group(frm) {
        if (cint(frm.doc.is_group)) frm.set_value("line_cost", 0);
        apply_budget_line_controls(frm);
        preview_budget_line_code(frm);
    },

    use_custom_code(frm) {
        if (!cint(frm.doc.use_custom_code)) {
            frm.set_value("budget_line", "");
            preview_budget_line_code(frm);
        }
        apply_budget_line_controls(frm);
    },

    status: apply_budget_line_controls,

    validate(frm) {
        validate_budget_line(frm);
    }
});

function set_budget_line_queries(frm) {
    frm.set_query("parent_budget_line", () => ({
        filters: {
            project: frm.doc.project || "",
            is_group: 1,
            status: ["!=", "Inactive"],
            name: ["!=", frm.doc.name || ""]
        }
    }));
}

function load_budget_line_currency(frm, overwrite = false) {
    if (!frm.doc.project || (frm.doc.currency && !overwrite)) return Promise.resolve();
    return frappe.db.get_doc("Project", frm.doc.project).then(project => {
        if (!project.company) return;
        return frappe.db.get_value("Company", project.company, "default_currency").then(r => {
            const currency = r.message ? r.message.default_currency : "";
            if (currency && (!frm.doc.currency || overwrite)) frm.set_value("currency", currency);
        });
    });
}

function load_parent_budget_line(frm) {
    if (!frm.doc.parent_budget_line) return Promise.resolve();
    if (frm.doc.parent_budget_line === frm.doc.name) {
        frm.set_value("parent_budget_line", "");
        frappe.throw(__("A Budget Line cannot be its own parent."));
    }
    return frappe.db.get_doc("Budget Line", frm.doc.parent_budget_line).then(parent => {
        if (parent.project !== frm.doc.project) {
            frm.set_value("parent_budget_line", "");
            frappe.throw(__("Parent Budget Line must belong to the selected Project."));
        }
        if (!cint(parent.is_group)) {
            frm.set_value("parent_budget_line", "");
            frappe.throw(__("Parent Budget Line must be a group."));
        }
        if (parent.status === "Inactive") {
            frm.set_value("parent_budget_line", "");
            frappe.throw(__("Inactive Budget Lines cannot be selected as parents."));
        }
        if (parent.currency) frm.set_value("currency", parent.currency);
    });
}

function apply_budget_line_controls(frm) {
    const isNew = frm.is_new();
    const isGroup = cint(frm.doc.is_group) === 1;
    const locked = cint(frm.doc.budget_line_locked) === 1;
    const inactive = frm.doc.status === "Inactive";
    const protectedRecord = locked || inactive;

    ["project", "is_group", "parent_budget_line", "use_custom_code"].forEach(fieldname => {
        frm.set_df_property(fieldname, "read_only", (!isNew || protectedRecord) ? 1 : 0);
    });

    frm.set_df_property(
        "budget_line", "read_only",
        (!isNew || !cint(frm.doc.use_custom_code) || protectedRecord) ? 1 : 0
    );

    ["name1", "more_details", "currency", "status"].forEach(fieldname => {
        frm.set_df_property(fieldname, "read_only", protectedRecord ? 1 : 0);
    });

    frm.set_df_property("line_cost", "read_only", (protectedRecord || isGroup) ? 1 : 0);
    frm.set_df_property("line_cost", "reqd", isGroup ? 0 : 1);

    if (frm.doc.status === "Approved" && !locked) {
        frm.dashboard.set_headline_alert(
            __("This approved Budget Line is temporarily open under an active Change Request."),
            "orange"
        );
    }
}

function preview_budget_line_code(frm) {
    if (!frm.is_new() || !frm.doc.project || cint(frm.doc.use_custom_code)) return;

    if (!frm.doc.parent_budget_line && cint(frm.doc.is_group)) {
        frm.set_value("budget_line", frm.doc.project);
        return;
    }
    if (!frm.doc.parent_budget_line) return;

    frappe.db.get_doc("Budget Line", frm.doc.parent_budget_line).then(parent => {
        return frappe.db.get_list("Budget Line", {
            filters: { project: frm.doc.project, parent_budget_line: frm.doc.parent_budget_line },
            fields: ["sequence"], order_by: "sequence desc", limit: 1
        }).then(rows => {
            const nextSequence = rows.length ? cint(rows[0].sequence) + 1 : 1;
            const parentIsRoot = !parent.parent_budget_line;
            let code = "";
            if (parentIsRoot) {
                if (nextSequence > BUDGET_TOP_LEVEL_CODES.length) {
                    frappe.msgprint(__("Automatic top-level coding supports A to Z. Use Donor Code for additional groups."));
                    return;
                }
                code = BUDGET_TOP_LEVEL_CODES[nextSequence - 1];
            } else {
                code = `${parent.budget_line}.${nextSequence}`;
            }
            frm.set_value("budget_line", code);
            frm.set_value("sequence", nextSequence);
        });
    });
}

function validate_budget_line(frm) {
    const isGroup = cint(frm.doc.is_group) === 1;
    const isRoot = isGroup && !frm.doc.parent_budget_line;

    if (!isRoot && !frm.doc.parent_budget_line) {
        frappe.throw(__("Every Budget Line except the Project root must have a Parent Budget Line."));
    }
    if (cint(frm.doc.use_custom_code) && !String(frm.doc.budget_line || "").trim()) {
        frappe.throw(__("Budget Line Code is required when Use Donor Code is enabled."));
    }
    if (flt(frm.doc.line_cost) < 0) {
        frappe.throw(__("Approved Budget Amount cannot be negative."));
    }
}

