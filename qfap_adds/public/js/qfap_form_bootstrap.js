// QFap global form bootstrap.
// Accounting dimensions and workflow are detected and initialized independently.
(() => {
    if (window.__qfap_form_bootstrap_loaded) return;
    window.__qfap_form_bootstrap_loaded = true;

    const PROJECT_FIELDS = ["project", "custom_project"];
    const BUDGET_FIELDS = ["budget_line", "custom_budget_line"];
    const STANDARD_DIMENSIONS = ["cost_center", "custom_cost_center"];
    const DIMENSION_CONTROLLER = "/assets/qfap_adds/js/transaction_controller.js";
    const WORKFLOW_CONTROLLER = "/assets/qfap_adds/js/document_workflow.js";
    let run_token = 0;

    const has_field = (meta, fieldname) =>
        Boolean((meta?.fields || []).find((field) => field.fieldname === fieldname));

    function configured_dimension_names() {
        const names = new Set(STANDARD_DIMENSIONS);
        (frappe.boot?.accounting_dimensions || []).forEach((dimension) => {
            if (typeof dimension === "string") {
                names.add(dimension);
                names.add(frappe.scrub(dimension));
                return;
            }
            [dimension?.fieldname, dimension?.document_type, dimension?.label]
                .filter(Boolean)
                .forEach((value) => names.add(frappe.scrub(value)));
        });
        return names;
    }

    function meta_has_dimensions(meta, dimension_names) {
        return (meta?.fields || []).some((field) => {
            if (!field.fieldname) return false;
            if (PROJECT_FIELDS.includes(field.fieldname)) return true;
            if (BUDGET_FIELDS.includes(field.fieldname)) {
                return field.fieldtype === "Link" && field.options === "Budget Line";
            }
            if (dimension_names.has(field.fieldname)) return true;
            return field.fieldtype === "Link" &&
                dimension_names.has(frappe.scrub(field.options || ""));
        });
    }

    async function form_has_dimensions(frm) {
        if (frm.doctype === "Budget Line") return false;
        const names = configured_dimension_names();
        if (meta_has_dimensions(frm.meta, names)) return true;

        const tables = (frm.meta?.fields || []).filter(
            (field) => field.fieldtype === "Table" && field.options
        );
        await Promise.all(
            tables.map((table) => frappe.model.with_doctype(table.options))
        );
        return tables.some((table) =>
            meta_has_dimensions(frappe.get_meta(table.options), names)
        );
    }

    function form_has_workflow(frm) {
        if (!frm) return false;
        if (frm.doc?.workflow_state) return true;
        if (has_field(frm.meta, "workflow_state")) return true;
        const workflow = frappe.workflow?.workflows?.[frm.doctype];
        return Boolean(workflow && workflow.name);
    }

    function require_asset(path) {
        return new Promise((resolve, reject) => {
            frappe.require(path, resolve, reject);
        });
    }

    async function initialize_current_form() {
        const token = ++run_token;
        await new Promise((resolve) => setTimeout(resolve, 80));
        const frm = window.cur_frm;
        if (!frm?.doctype || token !== run_token) return;

        // Workflow is initialized independently for every form. The workflow
        // controller itself exits cleanly when no active workflow is configured.
        await require_asset(WORKFLOW_CONTROLLER);
        if (token !== run_token || window.cur_frm !== frm) return;
        if (typeof window.qfap_initialize_document_workflow === "function") {
            window.qfap_initialize_document_workflow(frm);
        }

        if (await form_has_dimensions(frm)) {
            await require_asset(DIMENSION_CONTROLLER);
            if (token !== run_token || window.cur_frm !== frm) return;
            if (typeof window.qfap_initialize_transaction_controller === "function") {
                await window.qfap_initialize_transaction_controller(frm);
            }
        }
    }

    frappe.router.on("change", () => {
        initialize_current_form().catch((error) =>
            console.error("QFap form bootstrap failed", error)
        );
    });

    $(document).on("form-refresh", () => {
        initialize_current_form().catch((error) =>
            console.error("QFap form bootstrap failed", error)
        );
    });

    if (window.cur_frm) {
        initialize_current_form().catch((error) =>
            console.error("QFap form bootstrap failed", error)
        );
    }
})();
