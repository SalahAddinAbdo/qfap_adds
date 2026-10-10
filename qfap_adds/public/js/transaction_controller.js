// Dynamic Project and Budget Line controller for Frappe 16.
(() => {
    const frm = window.cur_frm;
    if (!frm || frm.__qfap_project_budget_loaded) return;
    frm.__qfap_project_budget_loaded = true;

    const PROJECT = ["project", "custom_project"];
    const BUDGET = ["budget_line", "custom_budget_line"];
    const field = (meta, names) => names.find((name) => (meta?.fields || []).some((df) => df.fieldname === name)) || "";
    const tables = () => (frm.meta.fields || []).filter((df) => df.fieldtype === "Table" && df.options);
    const parent_project_field = () => field(frm.meta, PROJECT);
    const parent_project = () => frm.doc[parent_project_field()] || "";

    const handlers = { setup: initialise, refresh: initialise, validate: synchronize };
    PROJECT.forEach((name) => {
        if (field(frm.meta, [name])) handlers[name] = async () => {
            await synchronize(true);
            configure_queries();
        };
    });
    frappe.ui.form.on(frm.doctype, handlers);

    async function initialise() {
        await load_metadata();
        register_child_events();
        configure_queries();
    }

    async function load_metadata() {
        await Promise.all(tables().map((table) => frappe.model.with_doctype(table.options)));
        const linked = new Set();
        const collect = (meta) => {
            const name = field(meta, BUDGET);
            const doctype = name ? meta.get_field(name)?.options : "";
            if (doctype) linked.add(doctype);
        };
        collect(frm.meta);
        tables().forEach((table) => collect(frappe.get_meta(table.options)));
        await Promise.all([...linked].map((doctype) => frappe.model.with_doctype(doctype)));
    }

    function register_child_events() {
        if (frm.__qfap_project_budget_child_events) return;
        frm.__qfap_project_budget_child_events = true;
        tables().forEach((table) => {
            const meta = frappe.get_meta(table.options);
            const project = field(meta, PROJECT);
            const budget = field(meta, BUDGET);
            if (!project) return;
            frappe.ui.form.on(table.options, {
                [project]: async (current, cdt, cdn) => {
                    const row = locals[cdt]?.[cdn];
                    if (budget && row?.[budget]) await frappe.model.set_value(cdt, cdn, budget, "");
                },
            });
        });
    }

    function configure_queries() {
        const project = parent_project();
        const parent_budget = field(frm.meta, BUDGET);
        if (parent_budget) frm.set_query(parent_budget, () => query_for(frm.meta, parent_budget, project));
        tables().forEach((table) => {
            const meta = frappe.get_meta(table.options);
            const project_field = field(meta, PROJECT);
            const budget_field = field(meta, BUDGET);
            const grid_field = budget_field ? frm.fields_dict[table.fieldname]?.grid?.get_field(budget_field) : null;
            if (!grid_field) return;
            grid_field.get_query = (doc, cdt, cdn) => {
                const row = locals[cdt]?.[cdn] || {};
                return query_for(meta, budget_field, (project_field && row[project_field]) || parent_project());
            };
        });
    }

    function query_for(owner_meta, budget_field, project) {
        if (!project) return { filters: { name: "__qfap_no_project__" } };
        const doctype = owner_meta.get_field(budget_field)?.options || "Budget Line";
        const project_field = field(frappe.get_meta(doctype), PROJECT) || "project";
        return { filters: { [project_field]: project } };
    }

    async function synchronize(parent_changed = false) {
        const project = parent_project();
        const parent_budget = field(frm.meta, BUDGET);
        if (parent_budget && frm.doc[parent_budget] && (!project || parent_changed || !(await matches(frm.meta, parent_budget, frm.doc[parent_budget], project)))) {
            await frm.set_value(parent_budget, "");
        }
        for (const table of tables()) {
            const meta = frappe.get_meta(table.options);
            const project_field = field(meta, PROJECT);
            const budget_field = field(meta, BUDGET);
            for (const row of frm.doc[table.fieldname] || []) {
                const changed = Boolean(project_field && row[project_field] !== project);
                if (changed) await frappe.model.set_value(row.doctype, row.name, project_field, project);
                if (budget_field && row[budget_field] && (!project || changed || !(await matches(meta, budget_field, row[budget_field], project)))) {
                    await frappe.model.set_value(row.doctype, row.name, budget_field, "");
                }
            }
        }
    }

    async function matches(owner_meta, budget_field, value, project) {
        if (!value || !project) return false;
        const doctype = owner_meta.get_field(budget_field)?.options || "Budget Line";
        await frappe.model.with_doctype(doctype);
        const project_field = field(frappe.get_meta(doctype), PROJECT) || "project";
        try {
            const response = await frappe.db.get_value(doctype, value, project_field);
            return response?.message?.[project_field] === project;
        } catch (error) {
            console.error("QFap Budget Line validation failed", error);
            return false;
        }
    }
})();
