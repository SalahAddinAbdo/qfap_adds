app_name = "qfap_adds"
app_title = "QFap Adds"
app_publisher = "QFap"
app_description = "Audit-focused extensions for ERPNext"
app_email = ""
app_license = "MIT"

required_apps = ["erpnext"]

doctype_js = {
    "Material Request": "public/js/transaction_controller.js",
    "Supplier Quotation": "public/js/transaction_controller.js",
    "Request for Quotation": "public/js/transaction_controller.js",
    "Purchase Order": "public/js/transaction_controller.js",
    "Purchase Receipt": "public/js/transaction_controller.js",
    "Purchase Invoice": "public/js/transaction_controller.js",
    "Stock Entry": "public/js/transaction_controller.js",
    "Journal Entry": "public/js/transaction_controller.js",
    "Expense Claim": "public/js/transaction_controller.js",
    "Payment Entry": "public/js/transaction_controller.js",
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
    ]]]},
]

after_install = "qfap_adds.qfap_adds.install.after_install"
after_migrate = "qfap_adds.qfap_adds.install.after_migrate"
