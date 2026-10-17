frappe.ui.form.on("Project Result", {
    setup(frm) { set_result_queries(frm); },
    refresh(frm) { set_result_queries(frm); toggle_result_code(frm); },
    project(frm) { frm.set_value("parent_result", ""); set_result_queries(frm); },
    result_level(frm) { frm.set_value("parent_result", ""); set_result_queries(frm); },
    use_custom_code(frm) { toggle_result_code(frm); }
});

function toggle_result_code(frm) {
    frm.set_df_property("result_code", "read_only", !cint(frm.doc.use_custom_code));
}

function set_result_queries(frm) {
    const parent_level = {"Outcome": "Impact / Goal", "Output": "Outcome"}[frm.doc.result_level];
    frm.set_query("parent_result", () => ({filters: {project: frm.doc.project || "", result_level: parent_level || "", status: ["!=", "Inactive"]}}));
    frm.set_query("responsible_employee", () => ({filters: {status: "Active"}}));
}
