// =========================================================
// Task Client Script - FINAL v2.1
// Frappe / ERPNext 16
// Replace the current Task Client Script completely.
//
// Required API Server Scripts:
//   task_assignment_scope
//   task_project_workplan_parent_options
//   reopen_task
//   task_unlock_parent_summary
//   task_complete_parent_summary
// =========================================================

function task_unique_names(values) {
    const output = [];
    (values || []).forEach((value) => {
        let name = "";
        if (typeof value === "string") {
            name = value;
        } else if (value && typeof value === "object") {
            name = value.name || value.employee || value.value || "";
        }
        if (name && !output.includes(name)) output.push(name);
    });
    return output;
}

function task_scope_payload(response) {
    const scope = (response && response.message) || {};
    return {
        current_employee: scope.current_employee || "",
        assignees: task_unique_names(
            scope.assignees || scope.assignable_employee_names || []
        ),
        supervisors: task_unique_names(
            scope.supervisors || scope.supervisor_names || []
        ),
        privileged: cint(scope.privileged || 0),
        can_manage_selected: cint(scope.can_manage_selected || 0),
        working_hours_per_day: flt(scope.working_hours_per_day || 8)
    };
}

function task_set_employee_queries(frm) {
    frm.set_query("custom_assign_to", () => {
        const names = (frm.__task_scope && frm.__task_scope.assignees) || [];
        const filters = [["Employee", "status", "=", "Active"]];
        filters.push([
            "Employee",
            "name",
            names.length ? "in" : "=",
            names.length ? names : "__no_authorized_employee__"
        ]);
        return {filters, ignore_user_permissions: true};
    });

    frm.set_query("custom_task_assigned_by", () => {
        const names = (frm.__task_scope && frm.__task_scope.supervisors) || [];
        const filters = [["Employee", "status", "=", "Active"]];
        filters.push([
            "Employee",
            "name",
            names.length ? "in" : "=",
            names.length ? names : "__no_authorized_supervisor__"
        ]);
        return {filters, ignore_user_permissions: true};
    });
}

function task_load_assignment_scope(frm, target_employee, preserve_values) {
    return frappe.call({
        method: "qfap_adds.qfap_adds.task_management.api.task_assignment_scope",
        args: {
            target_employee: target_employee || frm.doc.custom_assign_to || ""
        },
        freeze: false,
        callback: (response) => {
            const scope = task_scope_payload(response);
            frm.__task_scope = scope;
            task_set_employee_queries(frm);

            if (
                frm.is_new() &&
                !preserve_values &&
                !cint(frm.doc.custom_project_workplan || 0) &&
                !frm.doc.custom_assign_to &&
                scope.current_employee
            ) {
                frm.set_value("custom_assign_to", scope.current_employee);
            }

            ["custom_assign_to", "custom_task_assigned_by"].forEach(
                (fieldname) => {
                    if (frm.fields_dict[fieldname]) frm.refresh_field(fieldname);
                }
            );
        },
        error: () => {
            frm.__task_scope = {
                current_employee: "",
                assignees: [],
                supervisors: [],
                privileged: 0,
                can_manage_selected: 0
            };
            task_set_employee_queries(frm);
        }
    });
}

function task_get_parent_options(frm) {
    if (!frm.doc.project) {
        frappe.msgprint({
            title: __("Project Required"),
            indicator: "orange",
            message: __("Select the Project before choosing a Parent Task.")
        });
        return Promise.resolve([]);
    }

    return frappe.call({
        method: "qfap_adds.qfap_adds.task_management.api.task_project_workplan_parent_options",
        args: {
            project: frm.doc.project,
            current_task: frm.is_new() ? "" : (frm.doc.name || "")
        },
        freeze: true,
        freeze_message: __("Loading available main tasks...")
    }).then((response) => {
        const payload = (response && response.message) || {};
        return payload.options || [];
    });
}

function task_open_parent_dialog(frm) {
    task_get_parent_options(frm).then((options) => {
        if (!options.length) {
            frappe.msgprint({
                title: __("No Available Main Task"),
                indicator: "orange",
                message: __(
                    "No open and unlocked main task was found for the selected Project."
                )
            });
            return;
        }

        const normalized = options.map((item) => {
            if (typeof item === "string") {
                return {
                    label: item,
                    value: item,
                    category: "My Main Task",
                    subject: item,
                    status: "",
                    priority: "",
                    start_date: "",
                    end_date: ""
                };
            }
            return {
                label: item.label || item.subject || item.value || item.name || "",
                value: item.value || item.name || "",
                category: item.category || "My Main Task",
                subject: item.subject || item.label || item.value || "",
                status: item.status || "",
                priority: item.priority || "",
                start_date: item.start_date || "",
                end_date: item.end_date || "",
                progress: flt(item.progress || 0),
                expected_time: flt(item.expected_time || 0),
                actual_time: flt(item.actual_time || 0),
                child_count: cint(item.child_count || 0),
                completed_child_count: cint(item.completed_child_count || 0)
            };
        }).filter((item) => item.value);

        let dialog;

        function filter_options() {
            if (!dialog) return;

            const search = String(
                dialog.get_value("search_text") || ""
            ).trim().toLowerCase();
            const category = dialog.get_value("category_filter") || "All";

            const filtered = normalized.filter((item) => {
                const category_ok = category === "All" || item.category === category;
                const text = [
                    item.category,
                    item.subject,
                    item.value,
                    item.status,
                    item.priority,
                    item.start_date,
                    item.end_date
                ].join(" ").toLowerCase();
                return category_ok && (!search || text.includes(search));
            });

            const select_field = dialog.get_field("parent_task_choice");
            select_field.df.options = filtered.map((item) => ({
                label: item.label,
                value: item.value
            }));
            select_field.refresh();
            dialog.set_value("parent_task_choice", "");

            const summary = dialog.get_field("result_summary");
            if (summary && summary.$wrapper) {
                const workplans = filtered.filter(
                    (item) => item.category === "Project Workplan"
                ).length;
                summary.$wrapper.html(
                    `<div class="text-muted small" style="padding:6px 0 10px;">` +
                    `${__("Results")}: <strong>${filtered.length}</strong>` +
                    ` &nbsp; | &nbsp; ${__("Project Workplans")}: ` +
                    `<strong>${workplans}</strong>` +
                    ` &nbsp; | &nbsp; ${__("Accessible Main Tasks")}: ` +
                    `<strong>${filtered.length - workplans}</strong>` +
                    `</div>`
                );
            }
        }

        dialog = new frappe.ui.Dialog({
            title: __("Select Main Task"),
            size: "large",
            fields: [
                {
                    fieldname: "search_text",
                    label: __("Search"),
                    fieldtype: "Data",
                    description: __(
                        "Search by subject, task code, status, priority, or date."
                    ),
                    onchange: filter_options
                },
                {
                    fieldname: "category_filter",
                    label: __("Task Category"),
                    fieldtype: "Select",
                    options: ["All", "Project Workplan", "My Main Task"],
                    default: "All",
                    onchange: filter_options
                },
                {fieldname: "result_summary", fieldtype: "HTML"},
                {
                    fieldname: "parent_task_choice",
                    label: __("Main Task"),
                    fieldtype: "Select",
                    options: normalized.map((item) => ({
                        label: item.label,
                        value: item.value
                    })),
                    reqd: 1,
                    onchange() {
                        const selected = normalized.find(
                            (item) => item.value === dialog.get_value("parent_task_choice")
                        );
                        const field = dialog.get_field("selected_task_summary");
                        if (!field || !field.$wrapper) return;
                        if (!selected) {
                            field.$wrapper.empty();
                            return;
                        }
                        const esc = frappe.utils.escape_html;
                        field.$wrapper.html(
                            `<div class="alert alert-info" style="margin-top:10px;">` +
                            `<strong>${esc(selected.subject)}</strong><br>` +
                            `${__("Task")}: ${esc(selected.value)} &nbsp; | &nbsp; ` +
                            `${__("Status")}: ${esc(selected.status || "-")} &nbsp; | &nbsp; ` +
                            `${__("Progress")}: ${selected.progress}%<br>` +
                            `${__("Child Tasks")}: ${selected.completed_child_count}/${selected.child_count}` +
                            ` &nbsp; | &nbsp; ${__("Expected Hours")}: ${selected.expected_time}` +
                            ` &nbsp; | &nbsp; ${__("Actual Hours")}: ${selected.actual_time}` +
                            `</div>`
                        );
                    }
                },
                {fieldname: "selected_task_summary", fieldtype: "HTML"}
            ],
            primary_action_label: __("Select"),
            primary_action(values) {
                if (!values.parent_task_choice) return;
                frm.set_value("parent_task", values.parent_task_choice).then(() => {
                    dialog.hide();
                    frappe.show_alert({
                        message: __("Main Task selected successfully."),
                        indicator: "green"
                    });
                });
            }
        });

        dialog.show();
        filter_options();
    }).catch(() => {
        frappe.msgprint({
            title: __("Unable to Load Main Tasks"),
            indicator: "red",
            message: __("The available main tasks could not be loaded. Refresh the form and try again. If the issue continues, contact the System Administrator.")
        });
    });
}

function task_clear_parent_task(frm) {
    frm.set_value("parent_task", "");
    frappe.show_alert({message: __("Parent Task cleared."), indicator: "blue"});
}

function task_apply_workplan_ui(frm) {
    const is_workplan = cint(frm.doc.custom_project_workplan || 0) === 1;
    const employee_fields = [
        "custom_assign_to",
        "custom_self_assigned",
        "custom_task_assigned_by",
        "department",
        "custom_comments",
        "custom_supervisor_remarks"
    ];

    employee_fields.forEach((fieldname) => {
        frm.toggle_display(fieldname, !is_workplan);
    });

    frm.toggle_reqd("custom_assign_to", !is_workplan);
    frm.toggle_reqd(
        "custom_task_assigned_by",
        !is_workplan && !cint(frm.doc.custom_self_assigned || 0)
    );
    frm.toggle_reqd("department", !is_workplan);

    if (is_workplan) {
        const updates = {};
        if (!cint(frm.doc.is_group || 0)) updates.is_group = 1;
        if (frm.doc.custom_assign_to) updates.custom_assign_to = "";
        if (frm.doc.custom_task_assigned_by) updates.custom_task_assigned_by = "";
        if (cint(frm.doc.custom_self_assigned || 0)) updates.custom_self_assigned = 0;
        if (frm.doc.department) updates.department = "";
        if (Object.keys(updates).length) frm.set_value(updates);
    }
}

function task_apply_completion_lock_ui(frm) {
    const is_workplan = cint(frm.doc.custom_project_workplan || 0) === 1;
    const completed_locked = cint(frm.doc.custom_task_locked || 0) === 1;

    [
        "custom_assign_to",
        "custom_task_assigned_by",
        "custom_self_assigned"
    ].forEach((fieldname) => {
        if (frm.fields_dict[fieldname]) {
            frm.set_df_property(
                fieldname,
                "read_only",
                is_workplan || completed_locked ? 1 : 0
            );
        }
    });

    frm.set_df_property("parent_task", "read_only", 1);
    frm.set_df_property("completed_by", "read_only", 1);
    frm.set_df_property("completed_on", "read_only", 1);
    frm.set_df_property("closing_date", "read_only", 1);
}

function task_apply_parent_rollup_ui(frm) {
    const child_count = cint(frm.doc.custom_child_task_count || 0);
    const completed_count = cint(
        frm.doc.custom_completed_child_task_count || 0
    );
    const rollup_locked = cint(
        frm.doc.custom_parent_rollup_locked || 0
    ) === 1;
    const completed_locked = cint(frm.doc.custom_task_locked || 0) === 1;
    const form_locked = rollup_locked || completed_locked;

    // A main task becomes fully read-only immediately when its first
    // active child task is linked. Completed tasks are also fully locked.
    // Reload after an authorized unlock restores the normal editable form.
    if (form_locked) {
        frm.set_read_only();
        frm.disable_save();
        frm.page.clear_primary_action();
    }

    if (child_count > 0) {
        ["expected_time", "actual_time", "custom_expected_days", "exp_end_date", "progress"].forEach((fieldname) => {
            if (frm.fields_dict[fieldname]) frm.toggle_display(fieldname, true);
        });
    }

    // Rollup values always remain calculated when children exist, even
    // during an authorized one-time manual edit of other parent fields.
    ["progress", "expected_time", "actual_time"].forEach((fieldname) => {
        if (frm.fields_dict[fieldname]) {
            frm.set_df_property(
                fieldname,
                "read_only",
                child_count > 0 || completed_locked ? 1 : 0
            );
        }
    });

    if (child_count > 0) {
        frm.dashboard.add_comment(
            __(
                "Child tasks: {0} | Completed: {1} | Remaining: {2} | " +
                "Expected Hours: {3} | Actual Hours: {4}",
                [
                    child_count,
                    completed_count,
                    Math.max(child_count - completed_count, 0),
                    flt(frm.doc.expected_time || 0, 2),
                    flt(frm.doc.actual_time || 0, 2)
                ]
            ),
            completed_count === child_count ? "green" : "blue",
            true
        );

        if (rollup_locked && !completed_locked) {
            frm.set_intro(
                __(
                    "This main task is locked because it contains child tasks. " +
                    "Use Actions to unlock it for one manual edit, or complete it " +
                    "after all active child tasks are completed."
                ),
                "blue"
            );
        }
    }
}

function task_apply_timing_ui(frm) {
    const context = frm.doc.custom_task_timing_context || "Within Project Period";
    frm.toggle_reqd(
        "custom_comments",
        context !== "Within Project Period" &&
        !cint(frm.doc.custom_project_workplan || 0)
    );
}

function task_calculate_expected_values(frm, force_hours = false) {
    if (!frm.doc.exp_start_date || !frm.doc.exp_end_date) {
        if (flt(frm.doc.custom_expected_days || 0) !== 0) frm.set_value("custom_expected_days", 0);
        return;
    }
    const start = frappe.datetime.str_to_obj(frm.doc.exp_start_date);
    const end = frappe.datetime.str_to_obj(frm.doc.exp_end_date);
    if (!start || !end || end < start) return;
    const startDate = new Date(start.getFullYear(), start.getMonth(), start.getDate());
    const endDate = new Date(end.getFullYear(), end.getMonth(), end.getDate());
    const days = Math.round((endDate.getTime() - startDate.getTime()) / 86400000) + 1;
    frm.set_value("custom_expected_days", flt(days, 2));

    const hasChildren = cint(frm.doc.custom_child_task_count || 0) > 0;
    if (!hasChildren && (force_hours || flt(frm.doc.expected_time || 0) <= 0)) {
        const hoursPerDay = flt((frm.__task_scope || {}).working_hours_per_day || 8);
        frm.set_value("expected_time", flt(days * hoursPerDay, 2));
    }
}

function task_apply_self_assignment(frm) {
    if (cint(frm.doc.custom_project_workplan || 0) === 1) return;
    const self_assigned = cint(frm.doc.custom_self_assigned || 0) === 1;
    const current_employee =
        (frm.__task_scope && frm.__task_scope.current_employee) || "";

    frm.toggle_reqd("custom_task_assigned_by", !self_assigned);
    if (self_assigned && current_employee) {
        frm.set_value({
            custom_assign_to: current_employee,
            custom_task_assigned_by: current_employee
        });
    }
}

function task_set_completion_values(frm) {
    if (frm.doc.status !== "Completed") return;
    const updates = {};
    if (flt(frm.doc.progress || 0) !== 100) updates.progress = 100;
    if (!frm.doc.completed_on) {
        updates.completed_on = frappe.datetime.get_today();
    }
    if (!frm.doc.completed_by) updates.completed_by = frappe.session.user;
    if (!frm.doc.closing_date) {
        updates.closing_date = frappe.datetime.get_today();
    }
    if (Object.keys(updates).length) frm.set_value(updates);
}

function task_add_reopen_button(frm) {
    if (frm.is_new() || cint(frm.doc.custom_task_locked || 0) !== 1) return;
    frm.add_custom_button(
        __("Reopen Task"),
        () => {
            frappe.confirm(__("Reopen this completed task?"), () => {
                frappe.call({
                    method: "qfap_adds.qfap_adds.task_management.api.reopen_task",
                    args: {task: frm.doc.name},
                    freeze: true,
                    callback: (response) => {
                        if (!response.exc) frm.reload_doc();
                    }
                });
            });
        },
        __("Actions")
    );
}

function task_add_parent_unlock_button(frm) {
    if (
        frm.is_new() ||
        cint(frm.doc.custom_parent_rollup_locked || 0) !== 1 ||
        cint(frm.doc.custom_task_locked || 0) === 1
    ) {
        return;
    }

    frm.add_custom_button(
        __("Unlock Main Task for Editing"),
        () => {
            frappe.confirm(
                __(
                    "Unlock this main task for one manual edit? " +
                    "Progress and time totals will remain calculated from child tasks, " +
                    "and the main task will be locked again after saving."
                ),
                () => {
                    frappe.call({
                        method: "qfap_adds.qfap_adds.task_management.api.task_unlock_parent_summary",
                        args: {task: frm.doc.name},
                        freeze: true,
                        callback: (response) => {
                            if (!response.exc) frm.reload_doc();
                        }
                    });
                }
            );
        },
        __("Actions")
    );
}

function task_add_complete_parent_button(frm) {
    const child_count = cint(frm.doc.custom_child_task_count || 0);
    const completed_count = cint(
        frm.doc.custom_completed_child_task_count || 0
    );
    const completed_locked = cint(frm.doc.custom_task_locked || 0) === 1;

    if (
        frm.is_new() ||
        completed_locked ||
        child_count < 1 ||
        completed_count !== child_count
    ) {
        return;
    }

    frm.add_custom_button(
        __("Complete Main Task"),
        () => {
            frappe.confirm(
                __(
                    "All active child tasks are completed. Mark this main task as " +
                    "Completed and lock it?"
                ),
                () => {
                    frappe.call({
                        method: "qfap_adds.qfap_adds.task_management.api.task_complete_parent_summary",
                        args: {task: frm.doc.name},
                        freeze: true,
                        freeze_message: __("Completing main task..."),
                        callback: (response) => {
                            if (!response.exc) {
                                frappe.show_alert({
                                    message: __("Main task completed successfully."),
                                    indicator: "green"
                                });
                                frm.reload_doc();
                            }
                        }
                    });
                }
            );
        },
        __("Actions")
    );
}

function task_add_parent_buttons(frm) {
    const is_workplan = cint(frm.doc.custom_project_workplan || 0) === 1;
    const completed_locked = cint(frm.doc.custom_task_locked || 0) === 1;
    const rollup_locked = cint(frm.doc.custom_parent_rollup_locked || 0) === 1;

    if (!is_workplan && !completed_locked && !rollup_locked) {
        frm.add_custom_button(
            __("Select Parent Task"),
            () => task_open_parent_dialog(frm),
            __("Actions")
        );
    }

    if (frm.doc.parent_task && !completed_locked && !rollup_locked) {
        frm.add_custom_button(
            __("Clear Parent Task"),
            () => task_clear_parent_task(frm),
            __("Actions")
        );
    }
}


function task_add_supervisor_remark_button(frm) {
    if (frm.is_new() || cint(frm.doc.custom_project_workplan || 0)) return;
    frappe.call({
        method: "qfap_adds.qfap_adds.task_management.api.get_supervisor_remark_access",
        args: {task: frm.doc.name},
        freeze: false,
        callback(response) {
            const access = (response && response.message) || {};
            if (!cint(access.allowed || 0)) return;
            const current = access.current_remark || "";
            const label = current ? __("Update Supervisor Remark") : __("Add Supervisor Remark");
            frm.add_custom_button(label, () => {
                const dialog = new frappe.ui.Dialog({
                    title: label,
                    size: "large",
                    fields: [
                        {
                            fieldname: "current_remark",
                            label: __("Current Supervisor Remark"),
                            fieldtype: "Small Text",
                            default: current,
                            read_only: 1
                        },
                        {
                            fieldname: "remark",
                            label: __("Supervisor Remark"),
                            fieldtype: "Text Editor",
                            default: current,
                            reqd: 1,
                            description: __("Saving this remark notifies the Employee assigned to the Task.")
                        }
                    ],
                    primary_action_label: __("Save Remark"),
                    primary_action(values) {
                        frappe.call({
                            method: "qfap_adds.qfap_adds.task_management.api.save_supervisor_remark",
                            args: {task: frm.doc.name, remark: values.remark},
                            freeze: true,
                            freeze_message: __("Saving Supervisor Remark..."),
                            callback(r) {
                                dialog.hide();
                                if (r.message && r.message.changed) {
                                    frappe.show_alert({message: __("Supervisor Remark saved."), indicator: "green"});
                                }
                                frm.reload_doc();
                            }
                        });
                    }
                });
                dialog.show();
            }, __("Actions"));
        }
    });
}

frappe.ui.form.on("Task", {
    setup(frm) {
        frm.__task_scope = {
            current_employee: "",
            assignees: [],
            supervisors: [],
            privileged: 0,
            can_manage_selected: 0
        };
        task_set_employee_queries(frm);
    },

    onload(frm) {
        task_load_assignment_scope(
            frm,
            frm.doc.custom_assign_to || "",
            false
        );
    },

    refresh(frm) {
        task_set_employee_queries(frm);
        task_apply_workplan_ui(frm);
        task_apply_completion_lock_ui(frm);
        task_apply_parent_rollup_ui(frm);
        task_apply_timing_ui(frm);
        task_add_reopen_button(frm);
        task_add_parent_unlock_button(frm);
        task_add_complete_parent_button(frm);
        task_add_parent_buttons(frm);
        task_add_supervisor_remark_button(frm);
        frm.toggle_display("task_weight", false);
    },

    custom_assign_to(frm) {
        task_load_assignment_scope(
            frm,
            frm.doc.custom_assign_to || "",
            true
        );
    },

    custom_self_assigned(frm) {
        task_apply_self_assignment(frm);
    },

    custom_project_workplan(frm) {
        task_apply_workplan_ui(frm);
        task_apply_completion_lock_ui(frm);
        task_apply_parent_rollup_ui(frm);
        task_set_employee_queries(frm);
    },

    custom_task_timing_context(frm) {
        task_apply_timing_ui(frm);
    },

    project(frm) {
        if (frm.doc.parent_task) task_clear_parent_task(frm);
    },

    exp_start_date(frm) {
        task_calculate_expected_values(frm, true);
    },

    exp_end_date(frm) {
        task_calculate_expected_values(frm, true);
    },

    status(frm) {
        if (frm.doc.status === "Overdue") {
            frappe.msgprint({
                title: __("Calculated Status"),
                message: __(
                    "Overdue is calculated from the expected end date. " +
                    "Select the operational status instead."
                ),
                indicator: "orange"
            });
            frm.set_value("status", "Working");
            return;
        }
        task_set_completion_values(frm);
    },

    validate(frm) {
        if (frm.doc.status === "Completed") {
            frm.doc.progress = 100;
            if (!frm.doc.completed_on) {
                frm.doc.completed_on = frappe.datetime.get_today();
            }
            if (!frm.doc.completed_by) {
                frm.doc.completed_by = frappe.session.user;
            }
            if (!frm.doc.closing_date) {
                frm.doc.closing_date = frappe.datetime.get_today();
            }
        }

        if (frm.doc.exp_start_date && frm.doc.exp_end_date) {
            const start = frappe.datetime.str_to_obj(frm.doc.exp_start_date);
            const end = frappe.datetime.str_to_obj(frm.doc.exp_end_date);
            if (start && end && end < start) {
                frappe.throw(__(
                    "Expected End Date cannot be before Expected Start Date."
                ));
            }
        }

        if (!frm.doc.project) {
            frappe.throw(__("Project is required for every task."));
        }

        if (!cint(frm.doc.custom_project_workplan || 0)) {
            if (!frm.doc.custom_assign_to) {
                frappe.throw(__("Assign To is required."));
            }
            if (
                !cint(frm.doc.custom_self_assigned || 0) &&
                !frm.doc.custom_task_assigned_by
            ) {
                frappe.throw(__(
                    "Task Assigned By is required when the task is not self-assigned."
                ));
            }
        }

        const timing =
            frm.doc.custom_task_timing_context || "Within Project Period";
        if (
            timing !== "Within Project Period" &&
            !cint(frm.doc.custom_project_workplan || 0) &&
            !String(frm.doc.custom_comments || "").trim()
        ) {
            frappe.throw(__(
                "Comments are required when the task is outside the project period."
            ));
        }
    },

    after_save(frm) {
        task_load_assignment_scope(
            frm,
            frm.doc.custom_assign_to || "",
            true
        );
    }
});
