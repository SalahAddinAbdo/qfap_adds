// QFap adaptive Project, Budget Line, and accounting-dimension controller.
// Loaded by qfap_form_bootstrap.js only for forms that contain relevant fields.
window.qfap_initialize_transaction_controller = async function (frm) {
    frm = frm || window.cur_frm;
    if (!frm || frm.doctype === "Budget Line" || frm.__qfap_dimensions_v119_loaded) return;
    frm.__qfap_dimensions_v119_loaded = true;

    const PROJECT_FIELDS = ["project", "custom_project"];
    const BUDGET_FIELDS = ["budget_line", "custom_budget_line"];
    const STANDARD_DIMENSIONS = ["cost_center", "custom_cost_center"];
    const dimension_fields = new Set(STANDARD_DIMENSIONS);

    const docfield = (meta, fieldname) =>
        (meta?.fields || []).find((field) => field.fieldname === fieldname);
    const first_field = (meta, candidates) =>
        candidates.find((fieldname) => Boolean(docfield(meta, fieldname))) || "";
    const first_budget_field = (meta) =>
        BUDGET_FIELDS.find((fieldname) => {
            const field = docfield(meta, fieldname);
            return field?.fieldtype === "Link" && field.options === "Budget Line";
        }) || "";
    const table_fields = () =>
        (frm.meta?.fields || []).filter(
            (field) => field.fieldtype === "Table" && field.options
        );
    const parent_project_field = () => first_field(frm.meta, PROJECT_FIELDS);
    const parent_budget_field = () => first_budget_field(frm.meta);
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
        if (!docfield(frm.meta, fieldname)) return;
        handlers[fieldname] = async () => {
            await on_parent_project_change();
            configure_budget_queries();
        };
    });

    BUDGET_FIELDS.forEach((fieldname) => {
        if (first_budget_field(frm.meta) !== fieldname) return;
        handlers[fieldname] = async () => {
            await on_parent_budget_change();
            configure_budget_queries();
        };
    });

    frappe.ui.form.on(frm.doctype, handlers);

    async function initialize() {
        await load_metadata();
        discover_accounting_dimensions();
        register_parent_dimension_events();
        register_child_events();
        configure_budget_queries();
        await initialize_blank_rows();
    }

    async function load_metadata() {
        await Promise.all(
            table_fields().map((table) => frappe.model.with_doctype(table.options))
        );

        const linked_doctypes = new Set();
        const collect_budget_doctype = (meta) => {
            const fieldname = first_budget_field(meta);
            const doctype = fieldname ? docfield(meta, fieldname)?.options : "";
            if (doctype) linked_doctypes.add(doctype);
        };

        collect_budget_doctype(frm.meta);
        table_fields().forEach((table) =>
            collect_budget_doctype(frappe.get_meta(table.options))
        );
        await Promise.all(
            [...linked_doctypes].map((doctype) => frappe.model.with_doctype(doctype))
        );
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

        (frm.meta?.fields || []).forEach((field) => {
            if (!field.fieldname || field.fieldtype !== "Link") return;
            const is_dimension =
                STANDARD_DIMENSIONS.includes(field.fieldname) ||
                configured.has(field.fieldname) ||
                configured.has(frappe.scrub(field.options || ""));
            if (!is_dimension) return;
            if (
                table_fields().some((table) =>
                    docfield(frappe.get_meta(table.options), field.fieldname)
                )
            ) {
                dimension_fields.add(field.fieldname);
            }
        });
    }

    function register_parent_dimension_events() {
        if (frm.__qfap_parent_dimension_events_v118) return;
        frm.__qfap_parent_dimension_events_v118 = true;
        const dynamic_handlers = {};

        [...dimension_fields].forEach((fieldname) => {
            if (!docfield(frm.meta, fieldname)) return;
            dynamic_handlers[fieldname] = async () => {
                await overwrite_child_dimension(fieldname, frm.doc[fieldname] || "");
            };
        });

        if (Object.keys(dynamic_handlers).length) {
            frappe.ui.form.on(frm.doctype, dynamic_handlers);
        }
    }

    function register_child_events() {
        if (frm.__qfap_child_dimension_events_v118) return;
        frm.__qfap_child_dimension_events_v118 = true;

        table_fields().forEach((table) => {
            const child_meta = frappe.get_meta(table.options);
            const project_field = first_field(child_meta, PROJECT_FIELDS);
            const child_handlers = {};

            child_handlers[`${table.fieldname}_add`] = async (current, cdt, cdn) => {
                await initialize_new_row(locals[cdt]?.[cdn]);
            };

            if (project_field) {
                child_handlers[project_field] = async (current, cdt, cdn) => {
                    const row = locals[cdt]?.[cdn];
                    if (!row || row.__qfap_project_event_running) return;
                    row.__qfap_project_event_running = true;
                    try {
                        const budget_field = first_budget_field(child_meta);
                        // A changed or removed project invalidates the previous budget choice.
                        if (budget_field && row[budget_field]) {
                            await frappe.model.set_value(cdt, cdn, budget_field, "");
                        }
                        configure_budget_queries();
                    } finally {
                        delete row.__qfap_project_event_running;
                    }
                };
            }

            frappe.ui.form.on(table.options, child_handlers);
        });
    }

    async function on_parent_project_change() {
        const project = parent_project();
        const budget_field = parent_budget_field();

        // The previous header budget is never retained across a project change.
        if (budget_field && frm.doc[budget_field]) {
            await frm.set_value(budget_field, "");
        }

        for (const table of table_fields()) {
            const child_meta = frappe.get_meta(table.options);
            const child_project = first_field(child_meta, PROJECT_FIELDS);
            const child_budget = first_budget_field(child_meta);

            for (const row of frm.doc[table.fieldname] || []) {
                // Header changes deliberately overwrite user row overrides. Users may
                // choose different row values again after the header synchronization.
                if (child_budget && row[child_budget]) {
                    await frappe.model.set_value(row.doctype, row.name, child_budget, "");
                }
                if (child_project && row[child_project] !== project) {
                    await frappe.model.set_value(
                        row.doctype,
                        row.name,
                        child_project,
                        project
                    );
                }
            }
        }
    }

    async function on_parent_budget_change() {
        const project = parent_project();
        const budget = parent_budget();
        const budget_field = parent_budget_field();
        if (!budget_field) return;

        // A header Budget Line is valid only after a header Project is selected.
        if (!project && budget) {
            await frm.set_value(budget_field, "");
            frappe.show_alert({
                message: __("Select a Project before selecting a Budget Line."),
                indicator: "orange",
            });
            return;
        }

        if (budget && !(await budget_matches(frm.meta, budget_field, budget, project))) {
            await frm.set_value(budget_field, "");
            frappe.throw(__("The selected Budget Line does not belong to Project {0}.", [project]));
        }

        for (const table of table_fields()) {
            const child_meta = frappe.get_meta(table.options);
            const child_project = first_field(child_meta, PROJECT_FIELDS);
            const child_budget = first_budget_field(child_meta);
            if (!child_budget) continue;

            for (const row of frm.doc[table.fieldname] || []) {
                if (child_project && row[child_project] !== project) {
                    await frappe.model.set_value(
                        row.doctype,
                        row.name,
                        child_project,
                        project
                    );
                }
                if (row[child_budget] !== budget) {
                    await frappe.model.set_value(
                        row.doctype,
                        row.name,
                        child_budget,
                        budget
                    );
                }
            }
        }
    }

    async function overwrite_child_dimension(fieldname, value) {
        for (const table of table_fields()) {
            const child_meta = frappe.get_meta(table.options);
            if (!docfield(child_meta, fieldname)) continue;
            for (const row of frm.doc[table.fieldname] || []) {
                if (row[fieldname] !== value) {
                    await frappe.model.set_value(
                        row.doctype,
                        row.name,
                        fieldname,
                        value
                    );
                }
            }
        }
    }

    async function initialize_new_row(row) {
        if (!row) return;
        const child_meta = frappe.get_meta(row.doctype);
        const child_project = first_field(child_meta, PROJECT_FIELDS);
        const child_budget = first_budget_field(child_meta);
        const project = parent_project();
        const budget = parent_budget();

        if (child_project && parent_project_field()) {
            await frappe.model.set_value(row.doctype, row.name, child_project, project);
        }
        if (
            child_budget && budget && project &&
            (await budget_matches(child_meta, child_budget, budget, project))
        ) {
            await frappe.model.set_value(row.doctype, row.name, child_budget, budget);
        }

        for (const fieldname of dimension_fields) {
            if (!docfield(child_meta, fieldname) || !docfield(frm.meta, fieldname)) continue;
            await frappe.model.set_value(
                row.doctype,
                row.name,
                fieldname,
                frm.doc[fieldname] || ""
            );
        }
    }

    async function initialize_blank_rows() {
        for (const table of table_fields()) {
            const child_meta = frappe.get_meta(table.options);
            const child_project = first_field(child_meta, PROJECT_FIELDS);
            const child_budget = first_budget_field(child_meta);
            const project = parent_project();
            const budget = parent_budget();

            for (const row of frm.doc[table.fieldname] || []) {
                if (
                    child_project && parent_project_field() &&
                    project && !row[child_project]
                ) {
                    await frappe.model.set_value(
                        row.doctype,
                        row.name,
                        child_project,
                        project
                    );
                }
                if (
                    child_budget && budget && project && !row[child_budget] &&
                    (await budget_matches(child_meta, child_budget, budget, project))
                ) {
                    await frappe.model.set_value(
                        row.doctype,
                        row.name,
                        child_budget,
                        budget
                    );
                }
                for (const fieldname of dimension_fields) {
                    if (
                        docfield(child_meta, fieldname) &&
                        docfield(frm.meta, fieldname) &&
                        frm.doc[fieldname] && !row[fieldname]
                    ) {
                        await frappe.model.set_value(
                            row.doctype,
                            row.name,
                            fieldname,
                            frm.doc[fieldname]
                        );
                    }
                }
            }
        }
    }

    function configure_budget_queries() {
        const project = parent_project();
        const header_budget = parent_budget_field();

        if (header_budget) {
            frm.set_query(header_budget, () =>
                budget_query(frm.meta, header_budget, project)
            );
        }

        table_fields().forEach((table) => {
            const child_meta = frappe.get_meta(table.options);
            const child_project = first_field(child_meta, PROJECT_FIELDS);
            const child_budget = first_budget_field(child_meta);
            const grid_field = child_budget
                ? frm.fields_dict[table.fieldname]?.grid?.get_field(child_budget)
                : null;
            if (!grid_field) return;

            grid_field.get_query = (doc, cdt, cdn) => {
                const row = locals[cdt]?.[cdn] || {};
                return budget_query(
                    child_meta,
                    child_budget,
                    child_project ? row[child_project] || "" : project
                );
            };
        });
    }

    function budget_query(owner_meta, budget_field, project) {
        // Budget Lines are intentionally unavailable until a Project is selected.
        if (!project) {
            return { filters: { name: "__qfap_project_required__" } };
        }
        const budget_doctype =
            docfield(owner_meta, budget_field)?.options || "Budget Line";
        const budget_meta = frappe.get_meta(budget_doctype);
        const budget_project = first_field(budget_meta, PROJECT_FIELDS) || "project";
        return { filters: { [budget_project]: project } };
    }

    async function validate_rows() {
        const header_budget = parent_budget_field();
        if (header_budget && frm.doc[header_budget] && !parent_project()) {
            await frm.set_value(header_budget, "");
            frappe.throw(__("Select a Project before selecting a Budget Line."));
        }

        for (const table of table_fields()) {
            const child_meta = frappe.get_meta(table.options);
            const child_project = first_field(child_meta, PROJECT_FIELDS);
            const child_budget = first_budget_field(child_meta);
            if (!child_budget) continue;

            for (const row of frm.doc[table.fieldname] || []) {
                if (!row[child_budget]) continue;
                const project = child_project ? row[child_project] || "" : parent_project();
                if (!project) {
                    await frappe.model.set_value(
                        row.doctype,
                        row.name,
                        child_budget,
                        ""
                    );
                    frappe.throw(__("Select a Project in row {0} before selecting a Budget Line.", [row.idx]));
                }
                if (!(await budget_matches(child_meta, child_budget, row[child_budget], project))) {
                    await frappe.model.set_value(
                        row.doctype,
                        row.name,
                        child_budget,
                        ""
                    );
                    frappe.throw(__("Budget Line in row {0} does not belong to Project {1}.", [row.idx, project]));
                }
            }
        }
    }

    async function budget_matches(owner_meta, budget_field, value, project) {
        if (!value || !project) return false;
        const budget_doctype =
            docfield(owner_meta, budget_field)?.options || "Budget Line";
        await frappe.model.with_doctype(budget_doctype);
        const budget_meta = frappe.get_meta(budget_doctype);
        const budget_project = first_field(budget_meta, PROJECT_FIELDS) || "project";
        try {
            const response = await frappe.db.get_value(
                budget_doctype,
                value,
                budget_project
            );
            return response?.message?.[budget_project] === project;
        } catch (error) {
            console.error("QFap Budget Line validation failed", error);
            return false;
        }
    }

    // The asset can be loaded after the current form refresh event.
    await initialize();
};
