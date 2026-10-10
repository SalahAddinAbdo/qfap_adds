// QFap dynamic accounting-dimension controller.
(() => {
    if (!window.cur_frm || cur_frm.__qfap_dimensions_loaded) return;
    cur_frm.__qfap_dimensions_loaded = true;
    const dt = cur_frm.doctype;
    const handlers = {
        setup(frm) { qfap_setup_dimensions(frm); },
        refresh(frm) { qfap_setup_dimensions(frm); },
        validate(frm) { qfap_inherit_dimensions(frm); },
    };
    ["project", "custom_project"].forEach(fieldname => {
        if (frappe.meta.has_field(dt, fieldname)) handlers[fieldname] = frm => {
            qfap_inherit_dimensions(frm);
            qfap_setup_dimensions(frm);
        };
    });
    frappe.ui.form.on(dt, handlers);

    function qfap_setup_dimensions(frm) {
        (frm.meta.fields || []).filter(df => df.fieldtype === "Table" && df.options).forEach(df => {
            const grid = frm.fields_dict[df.fieldname]?.grid;
            if (!grid) return;
            const budget = grid.get_field("budget_line");
            if (budget) {
                budget.get_query = (doc, cdt, cdn) => {
                    const row = locals[cdt]?.[cdn] || {};
                    const project = row.project || frm.doc.project || frm.doc.custom_project;
                    return {filters: project ? {project, status: ["!=", "Inactive"]} : {name: "__none"}};
                };
            }
        });
        const budgetField = frm.get_field("budget_line");
        if (budgetField) budgetField.get_query = () => {
            const project = frm.doc.project || frm.doc.custom_project;
            return {filters: project ? {project, status: ["!=", "Inactive"]} : {name: "__none"}};
        };
    }

    function qfap_inherit_dimensions(frm) {
        const parentProject = frm.doc.project || frm.doc.custom_project || "";
        (frm.meta.fields || []).filter(df => df.fieldtype === "Table" && df.options).forEach(df => {
            (frm.doc[df.fieldname] || []).forEach(row => {
                if (parentProject && Object.prototype.hasOwnProperty.call(row, "project") && !row.project) {
                    frappe.model.set_value(row.doctype, row.name, "project", parentProject);
                }
                if (row.budget_line && !row.project && parentProject) {
                    frappe.model.set_value(row.doctype, row.name, "project", parentProject);
                }
            });
        });
    }
})();
