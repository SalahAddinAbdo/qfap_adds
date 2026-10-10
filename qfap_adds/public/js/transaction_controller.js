// QFap dynamic Project / Budget Line controller for Frappe 16.
(() => {
    const frm = window.cur_frm;
    if (!frm || frm.__qfap_dimensions_loaded) return;
    frm.__qfap_dimensions_loaded = true;

    const PROJECT_FIELDS = ["project", "custom_project"];
    const BUDGET_FIELDS = ["budget_line", "custom_budget_line"];
    const get_field = (meta, names) => names.find((name) => (meta?.fields || []).some((df) => df.fieldname === name)) || "";
    const table_fields = () => (frm.meta.fields || []).filter((df) => df.fieldtype === "Table" && df.options);
    const header_project_field = () => get_field(frm.meta, PROJECT_FIELDS);
    const header_project = () => frm.doc[header_project_field()] || "";

    const handlers = { setup: initialize, refresh: initialize, validate: synchronize };
    PROJECT_FIELDS.forEach((name) => {
        if (get_field(frm.meta, [name])) handlers[name] = async () => { await synchronize(true); configure_queries(); };
    });
    frappe.ui.form.on(frm.doctype, handlers);

    async function initialize() {
        await Promise.all(table_fields().map((table) => frappe.model.with_doctype(table.options)));
        const linked = new Set();
        const collect = (meta) => {
            const name = get_field(meta, BUDGET_FIELDS);
            const doctype = name ? meta.get_field(name)?.options : "";
            if (doctype) linked.add(doctype);
        };
        collect(frm.meta);
        table_fields().forEach((table) => collect(frappe.get_meta(table.options)));
        await Promise.all([...linked].map((doctype) => frappe.model.with_doctype(doctype)));
        register_child_events();
        configure_queries();
    }

    function register_child_events() {
        if (frm.__qfap_dimension_child_events) return;
        frm.__qfap_dimension_child_events = true;
        table_fields().forEach((table) => {
            const meta = frappe.get_meta(table.options);
            const project = get_field(meta, PROJECT_FIELDS);
            const budget = get_field(meta, BUDGET_FIELDS);
            if (!project) return;
            frappe.ui.form.on(table.options, {
                [project]: async (current, cdt, cdn) => {
                    const row = locals[cdt]?.[cdn];
                    if (budget && row?.[budget]) await frappe.model.set_value(cdt, cdn, budget, "");
                    const master = header_project();
                    if (row && row[project] !== master) await frappe.model.set_value(cdt, cdn, project, master);
                },
            });
        });
    }

    function configure_queries() {
        const project = header_project();
        const header_budget = get_field(frm.meta, BUDGET_FIELDS);
        if (header_budget) frm.set_query(header_budget, () => budget_query(frm.meta, header_budget, project));
        table_fields().forEach((table) => {
            const meta = frappe.get_meta(table.options);
            const project_field = get_field(meta, PROJECT_FIELDS);
            const budget_field = get_field(meta, BUDGET_FIELDS);
            const grid_field = budget_field ? frm.fields_dict[table.fieldname]?.grid?.get_field(budget_field) : null;
            if (!grid_field) return;
            grid_field.get_query = (doc, cdt, cdn) => {
                const row = locals[cdt]?.[cdn] || {};
                return budget_query(meta, budget_field, (project_field && row[project_field]) || header_project());
            };
        });
    }

    function budget_query(owner_meta, budget_field, project) {
        if (!project) return { filters: { name: "__qfap_no_project__" } };
        const doctype = owner_meta.get_field(budget_field)?.options || "Budget Line";
        const project_field = get_field(frappe.get_meta(doctype), PROJECT_FIELDS) || "project";
        return { filters: { [project_field]: project } };
    }

    async function synchronize(parent_changed = false) {
        const project = header_project();
        const header_budget = get_field(frm.meta, BUDGET_FIELDS);
        if (header_budget && frm.doc[header_budget] && (!project || parent_changed || !(await matches(frm.meta, header_budget, frm.doc[header_budget], project)))) await frm.set_value(header_budget, "");
        for (const table of table_fields()) {
            const meta = frappe.get_meta(table.options);
            const project_field = get_field(meta, PROJECT_FIELDS);
            const budget_field = get_field(meta, BUDGET_FIELDS);
            for (const row of frm.doc[table.fieldname] || []) {
                const changed = Boolean(project_field && row[project_field] !== project);
                if (changed) await frappe.model.set_value(row.doctype, row.name, project_field, project);
                if (budget_field && row[budget_field] && (!project || changed || !(await matches(meta, budget_field, row[budget_field], project)))) await frappe.model.set_value(row.doctype, row.name, budget_field, "");
            }
        }
    }

    async function matches(owner_meta, budget_field, value, project) {
        if (!value || !project) return false;
        const doctype = owner_meta.get_field(budget_field)?.options || "Budget Line";
        await frappe.model.with_doctype(doctype);
        const project_field = get_field(frappe.get_meta(doctype), PROJECT_FIELDS) || "project";
        try {
            const response = await frappe.db.get_value(doctype, value, project_field);
            return response?.message?.[project_field] === project;
        } catch (error) {
            console.error("QFap Budget Line validation failed", error);
            return false;
        }
    }
})();
