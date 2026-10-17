frappe.ui.form.on("Project Workplan Activity", {
    setup(frm) { set_activity_queries(frm); },
    refresh(frm) { set_activity_queries(frm); toggle_activity_code(frm); add_task_button(frm); },
    project(frm) {
        ["project_output","responsible_employee","responsible_department","implementation_partner","predecessor_activity","primary_budget_line"].forEach(field => frm.set_value(field, ""));
        set_activity_queries(frm);
    },
    async project_output(frm) {
        await fetch_activity_output_sector(frm);
        set_activity_queries(frm);
    },
    use_custom_code(frm) { toggle_activity_code(frm); },
    implementation_mode(frm) { if (frm.doc.implementation_mode === "Direct Implementation") frm.set_value("implementation_partner", ""); },
    progress_measurement_method(frm) {
        if (frm.doc.progress_measurement_method === "Percentage") { frm.set_value("unit_of_measure", "Percent"); frm.set_value("planned_quantity", 100); }
        if (frm.doc.progress_measurement_method === "Milestone") { frm.set_value("unit_of_measure", "Milestone"); frm.set_value("planned_quantity", 1); }
    }
});


async function fetch_activity_output_sector(frm) {
    if (!frm.doc.project_output) {
        await frm.set_value("sector", "");
        return;
    }

    const response = await frappe.db.get_value(
        "Project Result",
        frm.doc.project_output,
        ["project", "result_level", "sector", "status"]
    );
    const output = response.message || {};

    if (output.project && frm.doc.project && output.project !== frm.doc.project) {
        await frm.set_value("project_output", "");
        frappe.throw(__("Project Output must belong to the selected Project."));
    }
    if (output.result_level && output.result_level !== "Output") {
        await frm.set_value("project_output", "");
        frappe.throw(__("The selected Project Result must be an Output."));
    }
    if (!output.sector) {
        await frm.set_value("sector", "");
        frappe.throw(__("The selected Project Output does not have a Sector."));
    }

    await frm.set_value("sector", output.sector);
}

function toggle_activity_code(frm) {
    frm.set_df_property("activity_code", "read_only", !cint(frm.doc.use_custom_code));
}

function add_task_button(frm) {
    if (!frm.is_new() && frm.doc.linked_workplan_task) {
        frm.add_custom_button(__("Open Workplan Task"), () => frappe.set_route("Form", "Task", frm.doc.linked_workplan_task), __("Project"));
    }
}

function set_activity_queries(frm) {
    frm.set_query("project_output", () => ({filters: {project: frm.doc.project || "", result_level: "Output", status: ["!=", "Inactive"]}}));
    frm.set_query("responsible_employee", () => ({filters: {status: "Active"}}));
    frm.set_query("predecessor_activity", () => ({filters: {project: frm.doc.project || "", name: ["!=", frm.doc.name || ""]}}));
    frm.set_query("primary_budget_line", () => ({filters: {project: frm.doc.project || "", status: ["!=", "Inactive"]}}));
    frm.set_query("district", () => ({filters: {governorate: frm.doc.governorate || ""}}));
}
