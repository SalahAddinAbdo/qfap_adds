from __future__ import annotations

"""Explicit Q Org classification for standard ERPNext workspaces.

No item is classified by guessing from its name. Each target workspace, card,
and link is declared here. Missing workspaces, DocTypes, or Reports are skipped.
"""

STANDARD_WORKSPACE_INTEGRATIONS = (
    {
        "workspace_candidates": ("Projects", "Project"),
        "workspace_keywords": ("project",),
        "cards": (
            {
                "label": "Q Org - Planning & Results",
                "items": (
                    ("DocType", "Project Result", "Project Results"),
                    ("DocType", "Project Indicator", "Project Indicators"),
                    ("DocType", "Indicator Target Plan", "Indicator Target Plans"),
                    ("DocType", "Project Workplan Activity", "Workplan Activities"),
                ),
            },
            {
                "label": "Q Org - Monitoring & Control",
                "items": (
                    ("DocType", "Project Progress Update", "Progress Updates"),
                    ("DocType", "Project Risk", "Project Risks"),
                    ("DocType", "Project Change Request", "Change Requests"),
                    ("DocType", "Project Compliance Deliverable", "Compliance Deliverables"),
                ),
            },
            {
                "label": "Q Org - Delivery & Closure",
                "items": (
                    ("DocType", "Project Beneficiary Plan", "Beneficiary Plans"),
                    ("DocType", "Project Closure", "Project Closures"),
                    ("DocType", "Task Assignment Request", "Task Assignment Requests"),
                ),
            },
            {
                "label": "Q Org - Performance Reports",
                "items": (
                    ("Report", "Project Portfolio Overview", "Portfolio Overview"),
                    ("Report", "Project Progress", "Project Progress"),
                    ("Report", "Indicator Performance", "Indicator Performance"),
                    ("Report", "Beneficiary Reach", "Beneficiary Reach"),
                ),
            },
            {
                "label": "Q Org - Assurance Reports",
                "items": (
                    ("Report", "Project Risks and Issues", "Risks and Issues"),
                    ("Report", "Compliance Assurance", "Compliance Assurance"),
                    ("Report", "Change Control", "Change Control"),
                    ("Report", "Closure Readiness", "Closure Readiness"),
                    ("Report", "Project Data Quality", "Project Data Quality"),
                ),
            },
            {
                "label": "Q Org - Finance & Tasks",
                "items": (
                    ("Report", "Project Budget", "Project Budget"),
                    ("Report", "Budget Versus Actual", "Budget Versus Actual"),
                    ("Report", "Employees Task Tracker", "Employee Task Tracker"),
                ),
            },
        ),
    },
    {
        "workspace_candidates": ("Accounts", "Accounting", "Financial Accounting"),
        "workspace_keywords": ("account", "financial"),
        "cards": (
            {
                "label": "Q Org - Project Finance",
                "items": (
                    ("DocType", "Budget Line", "Budget Lines"),
                ),
            },
            {
                "label": "Q Org - Financial Reports",
                "items": (
                    ("Report", "Project Budget", "Project Budget"),
                    ("Report", "Budget Versus Actual", "Budget Versus Actual"),
                ),
            },
            {
                "label": "Q Org - Enhanced Ledger Reports",
                "items": (
                    ("Report", "Projects Ledger Summary", "Projects Ledger Summary"),
                    ("Report", "Projects Ledger Summary by Governorate", "Ledger by Governorate"),
                    ("Report", "Projects Ledger Summary by Partner", "Ledger by Partner"),
                    ("Report", "Projects Ledger Summary by Sector", "Ledger by Sector"),
                ),
            },
        ),
    },
    {
        "workspace_candidates": ("Human Resources", "HR", "HRMS"),
        "workspace_keywords": ("human resource", "hr"),
        "cards": (
            {
                "label": "Q Org - Task Forms",
                "items": (
                    ("DocType", "Task Assignment Request", "Task Assignment Requests"),
                ),
            },
            {
                "label": "Q Org - Task Reports",
                "items": (
                    ("Report", "Employees Task Tracker", "Employee Task Tracker"),
                ),
            },
        ),
    },
    {
        "workspace_candidates": ("Build", "Settings"),
        "workspace_keywords": ("build", "setting"),
        "cards": (
            {
                "label": "Q Org - Workflow",
                "items": (
                    ("DocType", "Workflow", "Workflows"),
                    ("DocType", "Workflow State", "Workflow States"),
                    ("DocType", "Workflow Action Master", "Workflow Actions"),
                ),
            },
            {
                "label": "Q Org - Documents & Printing",
                "items": (
                    ("DocType", "Employee Signature", "Employee Signatures"),
                    ("DocType", "Employee Signature Configuration", "Signature Configuration"),
                    ("DocType", "Print Settings", "Print Settings"),
                    ("DocType", "Print Format", "Print Formats"),
                    ("DocType", "Letter Head", "Letter Heads"),
                ),
            },
        ),
    },
)

MANAGED_CARD_PREFIX = "Q Org - "
