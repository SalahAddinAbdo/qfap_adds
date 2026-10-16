from __future__ import annotations

from qfap_adds.qfap_adds.task_management.services import validate_period
from qfap_adds.qfap_adds.task_management.settings import get_settings


class TaskProjectPeriodPolicyMixin:
    """Apply Farabi Task Management project-period policy to ERPNext Tasks.

    ERPNext calls ``validate_parent_project_dates`` from the standard Task
    controller. This mixin replaces only that project-boundary check. All other
    standard Task validations remain active.
    """

    def validate_parent_project_dates(self):
        settings = get_settings()

        # Disabling enforcement in Task Management Settings must also bypass
        # ERPNext's standard Project boundary validation.
        if not int(settings.enforce_project_period or 0):
            return

        validate_period(
            project=self.project,
            start_date=self.exp_start_date,
            end_date=self.exp_end_date,
            is_workplan=bool(self.get("custom_project_workplan")),
            throw=True,
        )
