frappe.treeview_settings["Budget Line"] = {
    breadcrumb: "QFap Adds",
    get_tree_nodes: "frappe.desk.treeview.get_children",
    add_tree_node: "frappe.desk.treeview.add_node",
    filters: [{fieldname: "project", fieldtype: "Link", options: "Project", label: __("Project")}],
    get_tree_root: false,
    root_label: "Budget Lines",
};
