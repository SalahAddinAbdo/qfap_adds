from __future__ import annotations

"""Controlled Q Org classification for standard ERPNext workspaces.

Only explicitly listed, app-owned DocTypes and Reports are integrated. No custom
reports created from the UI are inferred or included automatically.
"""

STANDARD_WORKSPACE_INTEGRATIONS = (
    {
        "workspace_candidates": ("Projects", "Project"),
        "workspace_keywords": ("project",),
        "cards": (
            {
                "label": "Q Org - Planning Forms",
                "items": (
                    ("DocType", "Project Result", "Project Results"),
                    ("DocType", "Project Indicator", "Project Indicators"),
                    ("DocType", "Indicator Target Plan", "Indicator Target Plans"),
                    ("DocType", "Project Workplan Activity", "Workplan Activities"),
                    ("DocType", "Project Beneficiary Plan", "Beneficiary Plans"),
                ),
            },
            {
                "label": "Q Org - Control Forms",
                "items": (
                    ("DocType", "Project Progress Update", "Progress Updates"),
                    ("DocType", "Project Risk", "Project Risks"),
                    ("DocType", "Project Change Request", "Change Requests"),
                    ("DocType", "Project Compliance Deliverable", "Compliance Deliverables"),
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
                    ("Report", "Project Data Quality", "Project Data Quality"),
                    ("Report", "Employees Task Tracker", "Employee Task Tracker"),
                ),
            },
            {
                "label": "Q Org - Assurance Reports",
                "items": (
                    ("Report", "Project Risks and Issues", "Risks and Issues"),
                    ("Report", "Compliance Assurance", "Compliance Assurance"),
                    ("Report", "Change Control", "Change Control"),
                    ("Report", "Closure Readiness", "Closure Readiness"),
                    ("Report", "Project Budget", "Project Budget"),
                    ("Report", "Budget Versus Actual", "Budget Versus Actual"),
                ),
            },
        ),
    },
    {
        "workspace_candidates": (
            "Financial Reports", "Accounts", "Accounting", "Financial Accounting",
        ),
        "workspace_keywords": ("financial report", "accounting", "accounts"),
        "cards": (
            {
                "label": "Q Org - Finance Forms",
                "items": (
                    ("DocType", "Budget Line", "Budget Lines"),
                ),
            },
            {
                "label": "Q Org - Finance Reports",
                "items": (
                    ("Report", "Enhanced General Ledger", "Enhanced General Ledger"),
                    ("Report", "Project Budget", "Project Budget"),
                    ("Report", "Budget Versus Actual", "Budget Versus Actual"),
                ),
            },
        ),
    },
    {
        "workspace_candidates": ("Human Resources", "HR", "HRMS"),
        "workspace_keywords": ("human resource", "hrms"),
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
        "workspace_keywords": ("build", "settings"),
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
