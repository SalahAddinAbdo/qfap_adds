// QFap adaptive accounting dimensions, Project, and Budget Line controller.
(() => {
    const frm = window.cur_frm;
    if (!frm || frm.__qfap_dimensions_v116_loaded) return;
    frm.__qfap_dimensions_v116_loaded = true;

    const PROJECT_FIELDS = ["project", "custom_project"];
    const BUDGET_FIELDS = ["budget_line", "custom_budget_line"];
    const STANDARD_DIMENSIONS = ["cost_center", "custom_cost_center"];
    const dimensions = new Set(STANDARD_DIMENSIONS);

    const df = (meta, fieldname) =>
        (meta?.fields || []).find((field) => field.fieldname === fieldname);
    const first = (meta, candidates) =>
        candidates.find((fieldname) => Boolean(df(meta, fieldname))) || "";
    const tables = () =>
        (frm.meta.fields || []).filter((field) => field.fieldtype === "Table" && field.options);
    const parent_project_field = () => first(frm.meta, PROJECT_FIELDS);
    const parent_budget_field = () => first(frm.meta, BUDGET_FIELDS);
    const parent_project = () => {
        const fieldname = parent_project_field();
        return fieldname ? frm.doc[fieldname] || "" : "";
    };
    const parent_budget = () => {
        const fieldname = parent_budget_field();
        return fieldname ? frm.doc[fieldname] || "" : "";
    };

    const handlers = {
        setup: initialize,
        refresh: initialize,
        validate: validate_rows,
    };

    PROJECT_FIELDS.forEach((fieldname) => {
        if (!df(frm.meta, fieldname)) return;
        handlers[fieldname] = async () => {
            await default_parent_project_to_blank_rows();
            configure_budget_queries();
        };
    });

    BUDGET_FIELDS.forEach((fieldname) => {
        if (!df(frm.meta, fieldname)) return;
        handlers[fieldname] = async () => {
            await default_parent_budget_to_compatible_rows();
            configure_budget_queries();
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
        await load_relevant_metadata();
        discover_accounting_dimensions();
        register_parent_dimension_events();
        register_child_events();
        configure_budget_queries();
        await default_missing_row_values();
        load_workflow_handler();
    }

    async function load_relevant_metadata() {
        await Promise.all(tables().map((table) => frappe.model.with_doctype(table.options)));
        const linked = new Set();
        const collect = (meta) => {
            const budget = first(meta, BUDGET_FIELDS);
            const doctype = budget ? df(meta, budget)?.options : "";
            if (doctype) linked.add(doctype);
        };
        collect(frm.meta);
        tables().forEach((table) => collect(frappe.get_meta(table.options)));
        await Promise.all([...linked].map((doctype) => frappe.model.with_doctype(doctype)));
    }

    function discover_accounting_dimensions() {
        const configured = new Set();
        (frappe.boot?.accounting_dimensions || []).forEach((dimension) => {
            if (typeof dimension === "string") {
                configured.add(dimension);
                configured.add(frappe.scrub(dimension));
                return;
            }
            [dimension?.fieldname, dimension?.document_type, dimension?.label]
                .filter(Boolean)
                .forEach((value) => configured.add(frappe.scrub(value)));
        });

        (frm.meta.fields || []).forEach((field) => {
            if (!field.fieldname || field.fieldtype !== "Link") return;
            const is_dimension =
                STANDARD_DIMENSIONS.includes(field.fieldname) ||
                configured.has(field.fieldname) ||
                configured.has(frappe.scrub(field.options || ""));
            if (!is_dimension) return;
            if (tables().some((table) => df(frappe.get_meta(table.options), field.fieldname))) {
                dimensions.add(field.fieldname);
            }
        });
    }

    function register_parent_dimension_events() {
        if (frm.__qfap_parent_dimension_events_v116) return;
        frm.__qfap_parent_dimension_events_v116 = true;
        const dynamic = {};
        [...dimensions].forEach((fieldname) => {
            if (!df(frm.meta, fieldname)) return;
            dynamic[fieldname] = async () => {
                await default_dimension_to_blank_rows(fieldname);
            };
        });
        if (Object.keys(dynamic).length) frappe.ui.form.on(frm.doctype, dynamic);
    }

    function register_child_events() {
        if (frm.__qfap_child_events_v116) return;
        frm.__qfap_child_events_v116 = true;

        tables().forEach((table) => {
            const child_meta = frappe.get_meta(table.options);
            const project = first(child_meta, PROJECT_FIELDS);
            const budget = first(child_meta, BUDGET_FIELDS);
            const child_handlers = {};

            // Frappe fires <table_fieldname>_add after a grid row is created.
            child_handlers[`${table.fieldname}_add`] = async (current, cdt, cdn) => {
                await default_row(locals[cdt]?.[cdn]);
            };

            if (project) {
                child_handlers[project] = async (current, cdt, cdn) => {
                    const row = locals[cdt]?.[cdn];
                    if (!row || !budget || !row[budget]) return;
                    if (!(await budget_matches(child_meta, budget, row[budget], row[project]))) {
                        await frappe.model.set_value(cdt, cdn, budget, "");
                    }
                };
            }

            frappe.ui.form.on(table.options, child_handlers);
        });
    }

    async function default_row(row) {
        if (!row) return;
        const child_meta = frappe.get_meta(row.doctype);
        const project = first(child_meta, PROJECT_FIELDS);
        const budget = first(child_meta, BUDGET_FIELDS);
        const master_project = parent_project();
        const master_budget = parent_budget();

        // Header values are defaults, never row locks. If the header field does
        // not exist, the row remains fully independent for multi-project entries.
        if (project && master_project && !row[project]) {
            await frappe.model.set_value(row.doctype, row.name, project, master_project);
        }
        if (
            budget && master_budget && !row[budget] &&
            (!project || !row[project] || row[project] === master_project) &&
            (await budget_matches(child_meta, budget, master_budget, row[project] || master_project))
        ) {
            await frappe.model.set_value(row.doctype, row.name, budget, master_budget);
        }

        for (const fieldname of dimensions) {
            const parent_value = frm.doc[fieldname] || "";
            if (parent_value && df(child_meta, fieldname) && !row[fieldname]) {
                await frappe.model.set_value(row.doctype, row.name, fieldname, parent_value);
            }
        }
    }

    async function default_missing_row_values() {
        for (const table of tables()) {
            for (const row of frm.doc[table.fieldname] || []) {
                await default_row(row);
            }
        }
    }

    async function default_parent_project_to_blank_rows() {
        const master = parent_project();
        if (!parent_project_field() || !master) return;
        for (const table of tables()) {
            const child_meta = frappe.get_meta(table.options);
            const project = first(child_meta, PROJECT_FIELDS);
            if (!project) continue;
            for (const row of frm.doc[table.fieldname] || []) {
                if (!row[project]) {
                    await frappe.model.set_value(row.doctype, row.name, project, master);
                }
            }
        }
    }

    async function default_parent_budget_to_compatible_rows() {
        const master_budget = parent_budget();
        const master_project = parent_project();
        if (!parent_budget_field() || !master_budget) return;
        for (const table of tables()) {
            const child_meta = frappe.get_meta(table.options);
            const project = first(child_meta, PROJECT_FIELDS);
            const budget = first(child_meta, BUDGET_FIELDS);
            if (!budget) continue;
            for (const row of frm.doc[table.fieldname] || []) {
                const row_project = project ? row[project] || master_project : master_project;
                if (
                    !row[budget] &&
                    (await budget_matches(child_meta, budget, master_budget, row_project))
                ) {
                    await frappe.model.set_value(row.doctype, row.name, budget, master_budget);
                }
            }
        }
    }

    async function default_dimension_to_blank_rows(fieldname) {
        const value = frm.doc[fieldname] || "";
        if (!value) return;
        for (const table of tables()) {
            const child_meta = frappe.get_meta(table.options);
            if (!df(child_meta, fieldname)) continue;
            for (const row of frm.doc[table.fieldname] || []) {
                if (!row[fieldname]) {
                    await frappe.model.set_value(row.doctype, row.name, fieldname, value);
                }
            }
        }
    }

    function configure_budget_queries() {
        const master_project = parent_project();
        const master_budget = parent_budget_field();
        if (master_budget) {
            frm.set_query(master_budget, () => budget_query(frm.meta, master_budget, master_project));
        }

        tables().forEach((table) => {
            const child_meta = frappe.get_meta(table.options);
            const project = first(child_meta, PROJECT_FIELDS);
            const budget = first(child_meta, BUDGET_FIELDS);
            const grid_field = budget
                ? frm.fields_dict[table.fieldname]?.grid?.get_field(budget)
                : null;
            if (!grid_field) return;
            grid_field.get_query = (doc, cdt, cdn) => {
                const row = locals[cdt]?.[cdn] || {};
                return budget_query(
                    child_meta,
                    budget,
                    (project && row[project]) || master_project
                );
            };
        });
    }

    function budget_query(owner_meta, budget_field, project) {
        // No project field/value means independent budgeting. Do not hide all
        // choices, which is required for Payroll Entry and similar doctypes.
        if (!project) return {};
        const budget_doctype = df(owner_meta, budget_field)?.options || "Budget Line";
        const budget_meta = frappe.get_meta(budget_doctype);
        const budget_project = first(budget_meta, PROJECT_FIELDS) || "project";
        return { filters: { [budget_project]: project } };
    }

    async function validate_rows() {
        await default_missing_row_values();
        for (const table of tables()) {
            const child_meta = frappe.get_meta(table.options);
            const project = first(child_meta, PROJECT_FIELDS);
            const budget = first(child_meta, BUDGET_FIELDS);
            if (!budget) continue;
            for (const row of frm.doc[table.fieldname] || []) {
                if (!row[budget]) continue;
                const row_project = project ? row[project] || "" : parent_project();
                if (row_project && !(await budget_matches(child_meta, budget, row[budget], row_project))) {
                    await frappe.model.set_value(row.doctype, row.name, budget, "");
                    frappe.throw(__("Budget Line in row {0} does not belong to Project {1}.", [row.idx, row_project]));
                }
            }
        }
    }

    async function budget_matches(owner_meta, budget_field, value, project) {
        if (!value || !project) return true;
        const budget_doctype = df(owner_meta, budget_field)?.options || "Budget Line";
        await frappe.model.with_doctype(budget_doctype);
        const budget_meta = frappe.get_meta(budget_doctype);
        const budget_project = first(budget_meta, PROJECT_FIELDS) || "project";
        try {
            const response = await frappe.db.get_value(budget_doctype, value, budget_project);
            return !response?.message?.[budget_project] || response.message[budget_project] === project;
        } catch (error) {
            console.error("QFap Budget Line validation failed", error);
            return false;
        }
    }
})();
