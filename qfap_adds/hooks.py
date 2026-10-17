app_name = "qfap_adds"
app_title = "QFap Adds"
app_publisher = "QFap"
app_description = "Audit-focused extensions for ERPNext"
app_email = ""
app_license = "MIT"

required_apps = ["erpnext"]

app_include_js = [
    "/assets/qfap_adds/js/qfap_form_bootstrap.js",
]

extend_doctype_class = {
    "Task": [
        "qfap_adds.qfap_adds.task_management.task_controller.TaskProjectPeriodPolicyMixin"
    ],
}

doctype_js = {
    "Task Assignment Request": "public/js/task_assignment_request.js",
    "Task": "public/js/task.js",
    "Employee": "public/js/employee_announcement.js",
    "Notification": "public/js/notification_configuration.js",
    "Workflow": "public/js/workflow_engine.js",
}

doc_events = {
    "Task": {
        "before_validate": "qfap_adds.qfap_adds.task_management.events.before_validate",
        "on_update": "qfap_adds.qfap_adds.task_management.events.on_update",
        "after_delete": "qfap_adds.qfap_adds.task_management.events.after_delete",
    },
    "Workflow": {
        "validate": (
            "qfap_adds.qfap_adds.workflow.provisioning."
            "validate_workflow_configuration"
        ),
        "on_update": (
            "qfap_adds.qfap_adds.workflow.provisioning."
            "ensure_current_responsible_user"
        ),
    },
    "*": {
        "validate": (
            "qfap_adds.qfap_adds.workflow.permissions."
            "validate_responsible_user"
        ),
    },
}

fixtures = [
    {"dt": "Custom Field", "filters": [["name", "in", [
        "Workflow Transition-custom_employee_signature_mapping_key",
        "Workflow Transition-custom_apply_employee_signature",
        "Workflow Transition-custom_notify_document_creator",
        "Workflow Transition-custom_column_break_6mqhf",
        "Workflow Transition-custom_section_break_h8b1r",
        "Workflow Transition-custom_target_role",
        "Workflow Transition-custom_target_user_field",
        "Workflow Transition-custom_workflow_prompt",
        "Workflow Transition-custom_assignment_required",
        "Employee-custom_welcome_email_sent_by",
        "Employee-custom_column_break_pihk4",
        "Employee-custom_welcome_email_sent_on",
        "Employee-custom_column_break_eqtxt",
        "Employee-custom_welcome_email_sent_for_joining_date",
        "Employee-custom_welcome_email_information",
        "Workflow-custom_current_responsible_user_field",
        "Company-custom_print_identity_and_colors",
        "Company-custom_print_document_header_color",
        "Company-custom_print_primary_color",
        "Company-custom_column_break_cdpt1",
        "Company-custom_print_accent_color",
        "Company-custom_print_light_color",
        "Company-custom_column_break_twxkf",
        "Company-custom_print_border_color",
    ]]]},
]

before_migrate = [
    "qfap_adds.qfap_adds.project_management.short_name_migration.prepare_short_project_doctype_names",
    "qfap_adds.qfap_adds.project_management.migration.prepare_standard_project_doctypes",
]


# Project-cycle integration with the standard Issue DocType.
doc_events["Issue"] = {
    "validate": "qfap_adds.qfap_adds.project_management.issue_integration.validate_issue",
    "on_update": "qfap_adds.qfap_adds.project_management.issue_integration.update_linked_risk",
}

after_install = [
    "qfap_adds.qfap_adds.install.after_install",
    "qfap_adds.qfap_adds.task_management.provisioning.provision_task_integration",
    "qfap_adds.qfap_adds.project_management.provisioning.provision_project_management",
    "qfap_adds.qfap_adds.project_management.workflow_provisioning.provision_project_workflows",
    "qfap_adds.qfap_adds.project_management.notifications.provision_project_notifications",
    "qfap_adds.qfap_adds.project_management.report_migration.cleanup_replaced_project_reports",
]
after_migrate = [
    "qfap_adds.qfap_adds.install.after_migrate",
    "qfap_adds.printing.provisioning.provision_universal_print_formats",
    "qfap_adds.qfap_adds.task_management.provisioning.provision_task_integration",
    "qfap_adds.qfap_adds.project_management.provisioning.provision_project_management",
]


scheduler_events = {
    "daily": [
        "qfap_adds.qfap_adds.project_management.monitoring.run_daily_project_monitoring"
    ],
    "cron": {
        "*/15 * * * *": [
            "qfap_adds.qfap_adds.task_management.scheduler.run_scheduled_task_summary"
        ]
    }
}

permission_query_conditions = {
    "Task": "qfap_adds.qfap_adds.task_management.permissions.task_query_condition",
    "Task Assignment Request": "qfap_adds.qfap_adds.task_management.permissions.request_query_condition",
    'Project Result': "qfap_adds.qfap_adds.project_management.permissions.project_result_query",
    'Project Indicator': "qfap_adds.qfap_adds.project_management.permissions.project_indicator_query",
    'Indicator Target Plan': "qfap_adds.qfap_adds.project_management.permissions.indicator_target_plan_query",
    'Project Workplan Activity': "qfap_adds.qfap_adds.project_management.permissions.project_workplan_activity_query",
    'Project Progress Update': "qfap_adds.qfap_adds.project_management.permissions.project_progress_update_query",
    'Project Risk': "qfap_adds.qfap_adds.project_management.permissions.project_risk_query",
    'Project Change Request': "qfap_adds.qfap_adds.project_management.permissions.project_change_request_query",
    'Project Compliance Deliverable': "qfap_adds.qfap_adds.project_management.permissions.project_compliance_deliverable_query",
    'Project Beneficiary Plan': "qfap_adds.qfap_adds.project_management.permissions.project_beneficiary_plan_query",
    'Project Closure': "qfap_adds.qfap_adds.project_management.permissions.project_closure_query",
}

has_permission = {
    "Task": "qfap_adds.qfap_adds.task_management.permissions.has_task_permission",
    "Task Assignment Request": "qfap_adds.qfap_adds.task_management.permissions.has_request_permission",
    'Project Result': "qfap_adds.qfap_adds.project_management.permissions.project_result_has",
    'Project Indicator': "qfap_adds.qfap_adds.project_management.permissions.project_indicator_has",
    'Indicator Target Plan': "qfap_adds.qfap_adds.project_management.permissions.indicator_target_plan_has",
    'Project Workplan Activity': "qfap_adds.qfap_adds.project_management.permissions.project_workplan_activity_has",
    'Project Progress Update': "qfap_adds.qfap_adds.project_management.permissions.project_progress_update_has",
    'Project Risk': "qfap_adds.qfap_adds.project_management.permissions.project_risk_has",
    'Project Change Request': "qfap_adds.qfap_adds.project_management.permissions.project_change_request_has",
    'Project Compliance Deliverable': "qfap_adds.qfap_adds.project_management.permissions.project_compliance_deliverable_has",
    'Project Beneficiary Plan': "qfap_adds.qfap_adds.project_management.permissions.project_beneficiary_plan_has",
    'Project Closure': "qfap_adds.qfap_adds.project_management.permissions.project_closure_has",
}
