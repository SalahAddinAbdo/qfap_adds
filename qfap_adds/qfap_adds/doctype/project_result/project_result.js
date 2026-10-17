frappe.ui.form.on("Project Result", {
    setup(frm) {
        frm.__project_team_employees = [];
        set_result_queries(frm);
    },
    async onload(frm) {
        await load_project_team_employees(frm);
        set_result_queries(frm);
    },
    async refresh(frm) {
        await load_project_team_employees(frm);
        set_result_queries(frm);
        toggle_result_code(frm);
    },
    async project(frm) {
        frm.set_value("parent_result", "");
        frm.set_value("responsible_employee", "");
        await load_project_team_employees(frm);
        set_result_queries(frm);
    },
    result_level(frm) { frm.set_value("parent_result", ""); set_result_queries(frm); },
    use_custom_code(frm) { toggle_result_code(frm); }
});


async function load_project_team_employees(frm) {
    frm.__project_team_employees = [];
    if (!frm.doc.project) return;

    const response = await frappe.call({
        method: "qfap_adds.qfap_adds.project_management.api.get_project_team_employees",
        args: {project: frm.doc.project},
        freeze: false
    });
    frm.__project_team_employees = response.message || [];
}

function project_team_employee_query(frm) {
    const employees = frm.__project_team_employees || [];
    return {
        filters: [
            ["Employee", "status", "=", "Active"],
            ["Employee", "name", employees.length ? "in" : "=", employees.length ? employees : "__no_project_team_employee__"]
        ]
    };
}

function toggle_result_code(frm) {
    frm.set_df_property("result_code", "read_only", !cint(frm.doc.use_custom_code));
}

function set_result_queries(frm) {
    const parent_level = {"Outcome": "Impact / Goal", "Output": "Outcome"}[frm.doc.result_level];
    frm.set_query("parent_result", () => ({filters: {project: frm.doc.project || "", result_level: parent_level || "", status: ["!=", "Inactive"]}}));
    frm.set_query("responsible_employee", () => project_team_employee_query(frm));
}
