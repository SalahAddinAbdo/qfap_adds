// QFap dynamic accounting dimensions, Project, and Budget Line controller.
(() => {
    const frm = window.cur_frm;
    if (!frm || frm.__qfap_dimensions_v115_loaded) return;
    frm.__qfap_dimensions_v115_loaded = true;

    const PROJECT_FIELDS = ["project", "custom_project"];
    const BUDGET_FIELDS = ["budget_line", "custom_budget_line"];
    const STANDARD_DIMENSIONS = ["project", "custom_project", "cost_center", "custom_cost_center"];
    const state = { dimension_fields: new Set(STANDARD_DIMENSIONS), initialized: false };

    const get_docfield = (meta, fieldname) =>
        (meta?.fields || []).find((df) => df.fieldname === fieldname);
    const get_fieldname = (meta, candidates) =>
        candidates.find((fieldname) => Boolean(get_docfield(meta, fieldname))) || "";
    const table_fields = () =>
        (frm.meta.fields || []).filter((df) => df.fieldtype === "Table" && df.options);
    const header_project_field = () => get_fieldname(frm.meta, PROJECT_FIELDS);
    const header_budget_field = () => get_fieldname(frm.meta, BUDGET_FIELDS);
    const header_project = () => frm.doc[header_project_field()] || "";

    const handlers = {
        setup: initialize,
        refresh: initialize,
        validate: () => synchronize_all({ overwrite_dimensions: false, overwrite_budget: false }),
    };

    PROJECT_FIELDS.forEach((fieldname) => {
        if (!get_docfield(frm.meta, fieldname)) return;
        handlers[fieldname] = async () => {
            await synchronize_project_change();
            configure_queries();
        };
    });

    BUDGET_FIELDS.forEach((fieldname) => {
        if (!get_docfield(frm.meta, fieldname)) return;
        handlers[fieldname] = async () => {
            await propagate_header_budget();
            configure_queries();
        };
    });

    frappe.ui.form.on(frm.doctype, handlers);
    load_workflow_handler();

    function load_workflow_handler() {
        frappe.require("/assets/qfap_adds/js/document_workflow.js", () => {
            if (typeof window.qfap_initialize_document_workflow === "function") {
                window.qfap_initialize_document_workflow(frm);
            }
        });
    }

    async function initialize() {
        await load_metadata();
        discover_shared_dimensions();
        register_child_events();
        register_dimension_events();
        configure_queries();
        await inherit_missing_values();
        load_workflow_handler();
        state.initialized = true;
    }

    async function load_metadata() {
        await Promise.all(table_fields().map((table) => frappe.model.with_doctype(table.options)));
        const linked_doctypes = new Set();
        const collect_budget_doctype = (meta) => {
            const fieldname = get_fieldname(meta, BUDGET_FIELDS);
            const doctype = fieldname ? get_docfield(meta, fieldname)?.options : "";
            if (doctype) linked_doctypes.add(doctype);
        };
        collect_budget_doctype(frm.meta);
        table_fields().forEach((table) => collect_budget_doctype(frappe.get_meta(table.options)));
        await Promise.all([...linked_doctypes].map((doctype) => frappe.model.with_doctype(doctype)));
    }

    function discover_shared_dimensions() {
        const accounting_dimension_names = new Set(
            (frappe.boot?.accounting_dimensions || []).flatMap((dimension) => {
                if (typeof dimension === "string") return [dimension];
                return [dimension?.fieldname, dimension?.document_type]
                    .filter(Boolean)
                    .map((value) => frappe.scrub(value));
            })
        );

        (frm.meta.fields || []).forEach((df) => {
            if (!df.fieldname || df.fieldtype !== "Link") return;
            const fieldname = df.fieldname;
            const is_known_dimension =
                STANDARD_DIMENSIONS.includes(fieldname) ||
                accounting_dimension_names.has(fieldname) ||
                accounting_dimension_names.has(frappe.scrub(df.options || ""));
            if (!is_known_dimension) return;
            if (table_fields().some((table) => get_docfield(frappe.get_meta(table.options), fieldname))) {
                state.dimension_fields.add(fieldname);
            }
        });
    }

    function register_dimension_events() {
        if (frm.__qfap_parent_dimension_events_registered) return;
        frm.__qfap_parent_dimension_events_registered = true;
        const dynamic = {};
        [...state.dimension_fields].forEach((fieldname) => {
            if (!get_docfield(frm.meta, fieldname) || PROJECT_FIELDS.includes(fieldname)) return;
            dynamic[fieldname] = async () => {
                await propagate_parent_dimension(fieldname, true);
                configure_queries();
            };
        });
        if (Object.keys(dynamic).length) frappe.ui.form.on(frm.doctype, dynamic);
    }

    function register_child_events() {
        if (frm.__qfap_dimension_child_events_registered) return;
        frm.__qfap_dimension_child_events_registered = true;

        table_fields().forEach((table) => {
            const child_meta = frappe.get_meta(table.options);
            const project_field = get_fieldname(child_meta, PROJECT_FIELDS);
            const budget_field = get_fieldname(child_meta, BUDGET_FIELDS);
            const child_handlers = {};

            child_handlers[`${table.fieldname}_add`] = async (current, cdt, cdn) => {
                await inherit_row(locals[cdt]?.[cdn], { overwrite_dimensions: true, overwrite_budget: true });
            };

            if (project_field) {
                child_handlers[project_field] = async (current, cdt, cdn) => {
                    const row = locals[cdt]?.[cdn];
                    if (!row || row.__qfap_project_syncing) return;
                    const master_project = header_project();
                    if (budget_field && row[budget_field]) {
                        await frappe.model.set_value(cdt, cdn, budget_field, "");
                    }
                    if (row[project_field] !== master_project) {
                        row.__qfap_project_syncing = true;
                        await frappe.model.set_value(cdt, cdn, project_field, master_project);
                        delete row.__qfap_project_syncing;
                    }
                    const master_budget_field = header_budget_field();
                    if (budget_field && master_budget_field && frm.doc[master_budget_field]) {
                        await frappe.model.set_value(cdt, cdn, budget_field, frm.doc[master_budget_field]);
                    }
                };
            }
            frappe.ui.form.on(table.options, child_handlers);
        });
    }

    async function synchronize_project_change() {
        const project = header_project();
        for (const table of table_fields()) {
            const child_meta = frappe.get_meta(table.options);
            const project_field = get_fieldname(child_meta, PROJECT_FIELDS);
            const budget_field = get_fieldname(child_meta, BUDGET_FIELDS);
            for (const row of frm.doc[table.fieldname] || []) {
                if (budget_field && row[budget_field]) {
                    await frappe.model.set_value(row.doctype, row.name, budget_field, "");
                }
                if (project_field && row[project_field] !== project) {
                    await frappe.model.set_value(row.doctype, row.name, project_field, project);
                }
            }
        }
        await propagate_header_budget();
    }

    async function propagate_header_budget() {
        const project = header_project();
        const parent_budget_field = header_budget_field();
        const parent_budget = parent_budget_field ? frm.doc[parent_budget_field] || "" : "";

        if (parent_budget && !(await budget_matches(frm.meta, parent_budget_field, parent_budget, project))) {
            await frm.set_value(parent_budget_field, "");
            return;
        }

        for (const table of table_fields()) {
            const child_meta = frappe.get_meta(table.options);
            const project_field = get_fieldname(child_meta, PROJECT_FIELDS);
            const budget_field = get_fieldname(child_meta, BUDGET_FIELDS);
            if (!budget_field) continue;
            for (const row of frm.doc[table.fieldname] || []) {
                if (project_field && row[project_field] !== project) {
                    await frappe.model.set_value(row.doctype, row.name, project_field, project);
                }
                if (row[budget_field] !== parent_budget) {
                    await frappe.model.set_value(row.doctype, row.name, budget_field, parent_budget);
                }
            }
        }
    }

    async function propagate_parent_dimension(fieldname, overwrite) {
        const value = frm.doc[fieldname] || "";
        for (const table of table_fields()) {
            const child_meta = frappe.get_meta(table.options);
            if (!get_docfield(child_meta, fieldname)) continue;
            for (const row of frm.doc[table.fieldname] || []) {
                if (overwrite || !row[fieldname]) {
                    if (row[fieldname] !== value) {
                        await frappe.model.set_value(row.doctype, row.name, fieldname, value);
                    }
                }
            }
        }
    }

    async function inherit_missing_values() {
        for (const table of table_fields()) {
            for (const row of frm.doc[table.fieldname] || []) {
                await inherit_row(row, { overwrite_dimensions: false, overwrite_budget: false });
            }
        }
    }

    async function inherit_row(row, options) {
        if (!row) return;
        const child_meta = frappe.get_meta(row.doctype);
        const project_field = get_fieldname(child_meta, PROJECT_FIELDS);
        const budget_field = get_fieldname(child_meta, BUDGET_FIELDS);
        const parent_project = header_project();
        const parent_budget_field = header_budget_field();
        const parent_budget = parent_budget_field ? frm.doc[parent_budget_field] || "" : "";

        if (project_field && (options.overwrite_dimensions || !row[project_field])) {
            if (row[project_field] !== parent_project) {
                await frappe.model.set_value(row.doctype, row.name, project_field, parent_project);
            }
        }
        if (budget_field && (options.overwrite_budget || !row[budget_field])) {
            if (row[budget_field] !== parent_budget) {
                await frappe.model.set_value(row.doctype, row.name, budget_field, parent_budget);
            }
        }
        for (const fieldname of state.dimension_fields) {
            if (PROJECT_FIELDS.includes(fieldname) || !get_docfield(child_meta, fieldname)) continue;
            const parent_value = frm.doc[fieldname] || "";
            if ((options.overwrite_dimensions || !row[fieldname]) && row[fieldname] !== parent_value) {
                await frappe.model.set_value(row.doctype, row.name, fieldname, parent_value);
            }
        }
    }

    function configure_queries() {
        const project = header_project();
        const parent_budget = header_budget_field();
        if (parent_budget) {
            frm.set_query(parent_budget, () => budget_query(frm.meta, parent_budget, project));
        }
        table_fields().forEach((table) => {
            const child_meta = frappe.get_meta(table.options);
            const project_field = get_fieldname(child_meta, PROJECT_FIELDS);
            const budget_field = get_fieldname(child_meta, BUDGET_FIELDS);
            const grid_field = budget_field
                ? frm.fields_dict[table.fieldname]?.grid?.get_field(budget_field)
                : null;
            if (!grid_field) return;
            grid_field.get_query = (doc, cdt, cdn) => {
                const row = locals[cdt]?.[cdn] || {};
                return budget_query(
                    child_meta,
                    budget_field,
                    (project_field && row[project_field]) || header_project()
                );
            };
        });
    }

    function budget_query(owner_meta, budget_field, project) {
        if (!project) return { filters: { name: "__qfap_no_project__" } };
        const budget_doctype = get_docfield(owner_meta, budget_field)?.options || "Budget Line";
        const budget_meta = frappe.get_meta(budget_doctype);
        const budget_project_field = get_fieldname(budget_meta, PROJECT_FIELDS) || "project";
        return { filters: { [budget_project_field]: project } };
    }

    async function synchronize_all(options) {
        for (const table of table_fields()) {
            for (const row of frm.doc[table.fieldname] || []) {
                await inherit_row(row, options);
                const child_meta = frappe.get_meta(row.doctype);
                const budget_field = get_fieldname(child_meta, BUDGET_FIELDS);
                const project_field = get_fieldname(child_meta, PROJECT_FIELDS);
                if (budget_field && row[budget_field]) {
                    const project = (project_field && row[project_field]) || header_project();
                    if (!(await budget_matches(child_meta, budget_field, row[budget_field], project))) {
                        await frappe.model.set_value(row.doctype, row.name, budget_field, "");
                    }
                }
            }
        }
    }

    async function budget_matches(owner_meta, budget_field, value, project) {
        if (!value || !project) return false;
        const budget_doctype = get_docfield(owner_meta, budget_field)?.options || "Budget Line";
        await frappe.model.with_doctype(budget_doctype);
        const budget_meta = frappe.get_meta(budget_doctype);
        const budget_project_field = get_fieldname(budget_meta, PROJECT_FIELDS) || "project";
        try {
            const response = await frappe.db.get_value(budget_doctype, value, budget_project_field);
            return response?.message?.[budget_project_field] === project;
        } catch (error) {
            console.error("QFap Budget Line validation failed", error);
            return false;
        }
    }
})();
