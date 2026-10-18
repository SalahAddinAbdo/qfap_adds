from __future__ import annotations

"""Controlled Q Org integration map for standard ERPNext workspaces.

Every Q Org DocType or Report that should appear in a standard workspace must be
listed explicitly here. This avoids guessing from names or modules and keeps
navigation deterministic across environments.
"""

STANDARD_WORKSPACE_INTEGRATIONS = (
    {
        "workspace_candidates": ("Projects",),
        "cards": (
            {
                "label": "Q Org - Project Forms",
                "items": (
                    ("DocType", "Project Result", "Project Results"),
                    ("DocType", "Project Indicator", "Project Indicators"),
                    ("DocType", "Indicator Target Plan", "Indicator Target Plans"),
                    ("DocType", "Project Workplan Activity", "Workplan Activities"),
                    ("DocType", "Project Progress Update", "Progress Updates"),
                    ("DocType", "Project Risk", "Project Risks"),
                    ("DocType", "Project Change Request", "Change Requests"),
                    ("DocType", "Project Compliance Deliverable", "Compliance Deliverables"),
                    ("DocType", "Project Beneficiary Plan", "Beneficiary Plans"),
                    ("DocType", "Project Closure", "Project Closures"),
                    ("DocType", "Task Assignment Request", "Task Assignment Requests"),
                ),
            },
            {
                "label": "Q Org - Project Reports",
                "items": (
                    ("Report", "Project Portfolio Overview", "Portfolio Overview"),
                    ("Report", "Project Progress", "Project Progress"),
                    ("Report", "Indicator Performance", "Indicator Performance"),
                    ("Report", "Project Risks and Issues", "Risks and Issues"),
                    ("Report", "Beneficiary Reach", "Beneficiary Reach"),
                    ("Report", "Compliance Assurance", "Compliance Assurance"),
                    ("Report", "Change Control", "Change Control"),
                    ("Report", "Closure Readiness", "Closure Readiness"),
                    ("Report", "Project Data Quality", "Project Data Quality"),
                ),
            },
        ),
    },
    {
        "workspace_candidates": ("Accounts", "Accounting"),
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
        ),
    },
    {
        "workspace_candidates": ("Human Resources", "HR"),
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
)

# Only cards beginning with this prefix are owned and rebuilt by Q Org.
MANAGED_CARD_PREFIX = "Q Org - "
