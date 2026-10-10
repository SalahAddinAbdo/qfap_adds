// QFap dynamic Project / Budget Line controller for Frappe 16.
(() => {
    const frm = window.cur_frm;
    if (!frm || frm.__qfap_dimensions_loaded) return;
    frm.__qfap_dimensions_loaded = true;

    const PROJECT_FIELDS = ["project", "custom_project"];
    const BUDGET_FIELDS = ["budget_line", "custom_budget_line"];
    const get_docfield = (meta, fieldname) =>
        (meta?.fields || []).find((df) => df.fieldname === fieldname);
    const get_fieldname = (meta, candidates) =>
        candidates.find((fieldname) => Boolean(get_docfield(meta, fieldname))) || "";
    const table_fields = () =>
        (frm.meta.fields || []).filter((df) => df.fieldtype === "Table" && df.options);
    const header_project_field = () => get_fieldname(frm.meta, PROJECT_FIELDS);
    const header_project = () => frm.doc[header_project_field()] || "";

    const handlers = {
        setup: initialize,
        refresh: initialize,
        validate: synchronize,
    };

    PROJECT_FIELDS.forEach((fieldname) => {
        if (!get_docfield(frm.meta, fieldname)) return;
        handlers[fieldname] = async () => {
            await synchronize(true);
            configure_queries();
        };
    });

    frappe.ui.form.on(frm.doctype, handlers);
    load_workflow_handler();

    function load_workflow_handler() {
        frappe.require(
            "/assets/qfap_adds/js/document_workflow.js",
            () => {
                if (typeof window.qfap_initialize_document_workflow === "function") {
                    window.qfap_initialize_document_workflow(frm);
                }
            }
        );
    }

    async function initialize() {
        await Promise.all(
            table_fields().map((table) => frappe.model.with_doctype(table.options))
        );

        const linked_doctypes = new Set();
        const collect = (meta) => {
            const budget_field = get_fieldname(meta, BUDGET_FIELDS);
            const budget_doctype = budget_field
                ? get_docfield(meta, budget_field)?.options
                : "";
            if (budget_doctype) linked_doctypes.add(budget_doctype);
        };

        collect(frm.meta);
        table_fields().forEach((table) => collect(frappe.get_meta(table.options)));
        await Promise.all(
            [...linked_doctypes].map((doctype) => frappe.model.with_doctype(doctype))
        );

        register_child_events();
        configure_queries();
        load_workflow_handler();
    }

    function register_child_events() {
        if (frm.__qfap_dimension_child_events) return;
        frm.__qfap_dimension_child_events = true;

        table_fields().forEach((table) => {
            const meta = frappe.get_meta(table.options);
            const project_field = get_fieldname(meta, PROJECT_FIELDS);
            const budget_field = get_fieldname(meta, BUDGET_FIELDS);
            if (!project_field) return;

            frappe.ui.form.on(table.options, {
                [project_field]: async (current, cdt, cdn) => {
                    const row = locals[cdt]?.[cdn];
                    if (!row) return;

                    if (budget_field && row[budget_field]) {
                        await frappe.model.set_value(cdt, cdn, budget_field, "");
                    }

                    const project = header_project();
                    if (row[project_field] !== project) {
                        await frappe.model.set_value(cdt, cdn, project_field, project);
                    }
                },
            });
        });
    }

    function configure_queries() {
        const project = header_project();
        const header_budget = get_fieldname(frm.meta, BUDGET_FIELDS);
        if (header_budget) {
            frm.set_query(header_budget, () =>
                budget_query(frm.meta, header_budget, project)
            );
        }

        table_fields().forEach((table) => {
            const meta = frappe.get_meta(table.options);
            const project_field = get_fieldname(meta, PROJECT_FIELDS);
            const budget_field = get_fieldname(meta, BUDGET_FIELDS);
            const grid_field = budget_field
                ? frm.fields_dict[table.fieldname]?.grid?.get_field(budget_field)
                : null;
            if (!grid_field) return;

            grid_field.get_query = (doc, cdt, cdn) => {
                const row = locals[cdt]?.[cdn] || {};
                const project_value =
                    (project_field && row[project_field]) || header_project();
                return budget_query(meta, budget_field, project_value);
            };
        });
    }

    function budget_query(owner_meta, budget_field, project) {
        if (!project) {
            return { filters: { name: "__qfap_no_project__" } };
        }

        const budget_doctype =
            get_docfield(owner_meta, budget_field)?.options || "Budget Line";
        const budget_meta = frappe.get_meta(budget_doctype);
        const budget_project_field =
            get_fieldname(budget_meta, PROJECT_FIELDS) || "project";

        return { filters: { [budget_project_field]: project } };
    }

    async function synchronize(parent_changed = false) {
        const project = header_project();
        const header_budget = get_fieldname(frm.meta, BUDGET_FIELDS);

        if (
            header_budget &&
            frm.doc[header_budget] &&
            (
                !project ||
                parent_changed ||
                !(await budget_matches(frm.meta, header_budget, frm.doc[header_budget], project))
            )
        ) {
            await frm.set_value(header_budget, "");
        }

        for (const table of table_fields()) {
            const meta = frappe.get_meta(table.options);
            const project_field = get_fieldname(meta, PROJECT_FIELDS);
            const budget_field = get_fieldname(meta, BUDGET_FIELDS);

            for (const row of frm.doc[table.fieldname] || []) {
                const project_changed = Boolean(
                    project_field && row[project_field] !== project
                );

                if (project_changed) {
                    await frappe.model.set_value(
                        row.doctype,
                        row.name,
                        project_field,
                        project
                    );
                }

                if (
                    budget_field &&
                    row[budget_field] &&
                    (
                        !project ||
                        project_changed ||
                        !(await budget_matches(meta, budget_field, row[budget_field], project))
                    )
                ) {
                    await frappe.model.set_value(
                        row.doctype,
                        row.name,
                        budget_field,
                        ""
                    );
                }
            }
        }
    }

    async function budget_matches(owner_meta, budget_field, value, project) {
        if (!value || !project) return false;

        const budget_doctype =
            get_docfield(owner_meta, budget_field)?.options || "Budget Line";
        await frappe.model.with_doctype(budget_doctype);

        const budget_meta = frappe.get_meta(budget_doctype);
        const budget_project_field =
            get_fieldname(budget_meta, PROJECT_FIELDS) || "project";

        try {
            const response = await frappe.db.get_value(
                budget_doctype,
                value,
                budget_project_field
            );
            return response?.message?.[budget_project_field] === project;
        } catch (error) {
            console.error("QFap Budget Line validation failed", error);
            return false;
        }
    }
})();
