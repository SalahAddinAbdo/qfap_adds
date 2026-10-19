from __future__ import annotations

from qfap_adds.qfap_adds.project_management.services.project_reconciliation import reconcile_project


def rebuild_project_summary(project):
    """Backward-compatible wrapper around the authoritative reconciliation service."""
    return reconcile_project(project)
