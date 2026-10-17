app_name = "qfap_adds"
app_title = "QFap Adds"
app_publisher = "QFap"
app_description = "Audit-focused extensions for ERPNext"
app_email = ""
app_license = "MIT"

app_logo_url = "/assets/qfap_adds/images/qfap_project_cycle.png"
app_home = "/desk/qfap-management-hub"

add_to_apps_screen = [{
    "name": app_name,
    "logo": app_logo_url,
    "title": app_title,
    "route": app_home,
    "sequence_id": 5,
}]

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
    "Projects Settings": "public/js/projects_settings.js",
}

doc_events = {
    "Project Risk": {"on_update": "qfap_adds.qfap_adds.project_management.notification_engine.process_project_notification_on_update"},
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
    "qfap_adds.qfap_adds.project_management.workspace_migration.prepare_qfap_management_hub",
]

after_install = [
    "qfap_adds.qfap_adds.install.after_install",
    "qfap_adds.qfap_adds.task_management.provisioning.provision_task_integration",
    "qfap_adds.qfap_adds.project_management.provisioning.provision_project_management",
    "qfap_adds.qfap_adds.project_management.workflow_provisioning.provision_project_workflows",
    "qfap_adds.qfap_adds.project_management.notification_provisioning.provision_project_notifications",
    "qfap_adds.qfap_adds.project_management.navigation_provisioning.provision_project_navigation",
]
after_migrate = [
    "qfap_adds.qfap_adds.install.after_migrate",
    "qfap_adds.printing.provisioning.provision_universal_print_formats",
    "qfap_adds.qfap_adds.task_management.provisioning.provision_task_integration",
    "qfap_adds.qfap_adds.project_management.provisioning.provision_project_management",
    "qfap_adds.qfap_adds.project_management.workflow_provisioning.provision_project_workflows",
    "qfap_adds.qfap_adds.project_management.notification_provisioning.provision_project_notifications",
    "qfap_adds.qfap_adds.project_management.navigation_provisioning.provision_project_navigation",
]


scheduler_events = {
    "daily": ["qfap_adds.qfap_adds.project_management.notification_engine.run_daily_project_notifications"],
    "cron": {
        "*/15 * * * *": [
            "qfap_adds.qfap_adds.task_management.scheduler.run_scheduled_task_summary"
        ]
    }
}

permission_query_conditions = {
    "Task": "qfap_adds.qfap_adds.task_management.permissions.task_query_condition",
    "Task Assignment Request": "qfap_adds.qfap_adds.task_management.permissions.request_query_condition",
}

has_permission = {
    "Task": "qfap_adds.qfap_adds.task_management.permissions.has_task_permission",
    "Task Assignment Request": "qfap_adds.qfap_adds.task_management.permissions.has_request_permission",
}
