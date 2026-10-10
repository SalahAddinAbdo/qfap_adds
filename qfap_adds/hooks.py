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

doctype_js = {
    "Employee": "public/js/employee_announcement.js",
    "Notification": "public/js/notification_configuration.js",
    "Workflow": "public/js/workflow_engine.js",
}

doc_events = {
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

after_install = "qfap_adds.qfap_adds.install.after_install"
after_migrate = [
    "qfap_adds.qfap_adds.install.after_migrate",
    "qfap_adds.printing.provisioning.provision_universal_print_formats",
]
