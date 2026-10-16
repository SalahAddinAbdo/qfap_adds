from __future__ import annotations

import frappe

from qfap_adds.qfap_adds.task_management.settings import get_additional_recipient_emails, get_settings


def send_employee_task_summary(force=False):
    settings = get_settings()
    if not force and not int(settings.summary_schedule_enabled or 0):
        return {"sent": 0, "skipped": True}
    additional_recipients = get_additional_recipient_emails(settings)
    sent_count = 0
    # =========================================================
    # Scheduled Employee Task Summary
    # Frappe / ERPNext 16 - Safe Execution
    # Script Type: Scheduler Event
    # Event Frequency: Cron
    # Cron: 0 8 * * 0
    #
    # Design notes:
    # - Operational tasks drive workload KPIs, progress, and hour totals.
    # - Normal main tasks are shown in a separate summary section.
    # - Main-task rollup hours are NOT added to operational totals, avoiding
    #   double counting of child-task hours.
    # - Project Workplan tasks are excluded from the employee email.
    # =========================================================

    # ---------------------------------------------------------
    # Report dates
    # ---------------------------------------------------------

    today = frappe.utils.getdate(frappe.utils.nowdate())
    month_start = frappe.utils.getdate(frappe.utils.get_first_day(today))
    next_month_start = frappe.utils.getdate(
        frappe.utils.add_months(month_start, 1)
    )
    due_soon_end = frappe.utils.getdate(
        frappe.utils.add_days(today, 7)
    )
    site_url = frappe.utils.get_url()

    # ---------------------------------------------------------
    # Company identity
    # ---------------------------------------------------------

    default_company = (
        frappe.db.get_single_value(
            "Global Defaults",
            "default_company"
        )
        or ""
    )

    safe_default_company = frappe.utils.escape_html(default_company)
    management_signature = "Management"

    if safe_default_company:
        management_signature = safe_default_company + " Management"

    company_logo = ""

    if default_company:
        company_logo = (
            frappe.db.get_value(
                "Company",
                default_company,
                "company_logo"
            )
            or ""
        )

    company_logo_url = ""

    if company_logo:
        if (
            company_logo.startswith("http://")
            or company_logo.startswith("https://")
        ):
            company_logo_url = company_logo
        elif company_logo.startswith("/"):
            company_logo_url = site_url + company_logo
        else:
            company_logo_url = site_url + "/" + company_logo

    safe_company_logo_url = frappe.utils.escape_html(company_logo_url)
    company_logo_html = ""

    if safe_company_logo_url:
        company_logo_html = (
            '<img src="' + safe_company_logo_url + '" alt="' +
            safe_default_company + '" style="display:block;max-width:170px;'
            'max-height:85px;width:auto;height:auto;margin:0 0 0 auto;'
            'border:0;outline:none;text-decoration:none;" />'
        )

    # ---------------------------------------------------------
    # Active employees linked to enabled users with email
    # ---------------------------------------------------------

    employees = frappe.db.sql(
        """
        SELECT
            e.name AS employee,
            e.employee_name AS employee_name,
            e.department AS department,
            e.designation AS designation,
            e.user_id AS user_id,
            u.email AS email
        FROM `tabEmployee` e
        INNER JOIN `tabUser` u
            ON u.name = e.user_id
        WHERE
            e.status = 'Active'
            AND IFNULL(e.user_id, '') != ''
            AND IFNULL(u.enabled, 0) = 1
            AND IFNULL(u.email, '') != ''
        ORDER BY e.employee_name ASC
        """,
        as_dict=True
    )

    # ---------------------------------------------------------
    # Process each employee
    # ---------------------------------------------------------

    for employee in employees:
        employee_id = employee.get("employee") or ""
        employee_name = employee.get("employee_name") or employee_id
        recipient_email = (
            employee.get("email")
            or employee.get("user_id")
            or ""
        )
        department = employee.get("department") or ""
        designation = employee.get("designation") or ""

        if not employee_id or not recipient_email:
            continue

        # -----------------------------------------------------
        # Operational tasks only
        # -----------------------------------------------------

        tasks = frappe.db.sql(
            """
            SELECT
                t.name AS task,
                t.subject AS subject,
                t.project AS project,
                IFNULL(p.project_name, '') AS project_name,
                t.department AS department,
                t.type AS task_type,
                t.status AS status,
                t.priority AS priority,
                IFNULL(t.progress, 0) AS progress,
                t.exp_start_date AS exp_start_date,
                t.exp_end_date AS exp_end_date,
                IFNULL(t.custom_expected_days, 0) AS expected_days,
                IFNULL(t.expected_time, 0) AS expected_time,
                IFNULL(t.actual_time, 0) AS actual_time,
                IFNULL(t.is_milestone, 0) AS is_milestone,
                t.parent_task AS parent_task,
                t.completed_on AS completed_on,
                IFNULL(t.custom_task_locked, 0) AS task_locked,
                CASE
                    WHEN
                        t.status NOT IN ('Completed', 'Cancelled', 'Template')
                        AND t.exp_end_date IS NOT NULL
                        AND DATE(t.exp_end_date) < %(today)s
                    THEN 1 ELSE 0
                END AS is_overdue,
                CASE
                    WHEN
                        t.status NOT IN ('Completed', 'Cancelled', 'Template')
                        AND t.exp_end_date IS NOT NULL
                        AND DATE(t.exp_end_date) >= %(today)s
                        AND DATE(t.exp_end_date) <= %(due_soon_end)s
                    THEN 1 ELSE 0
                END AS is_due_soon,
                CASE
                    WHEN
                        t.status NOT IN ('Completed', 'Cancelled', 'Template')
                        AND t.exp_end_date IS NOT NULL
                        AND DATE(t.exp_end_date) < %(month_start)s
                    THEN 1 ELSE 0
                END AS is_carried_forward,
                CASE
                    WHEN
                        t.status NOT IN ('Completed', 'Cancelled', 'Template')
                        AND t.exp_end_date IS NOT NULL
                        AND DATE(t.exp_end_date) < %(today)s
                    THEN DATEDIFF(%(today)s, DATE(t.exp_end_date))
                    ELSE 0
                END AS delay_days
            FROM `tabTask` t
            LEFT JOIN `tabProject` p
                ON p.name = t.project
            WHERE
                t.custom_assign_to = %(employee)s
                AND IFNULL(t.is_template, 0) = 0
                AND IFNULL(t.is_group, 0) = 0
                AND IFNULL(t.custom_project_workplan, 0) = 0
                AND t.status NOT IN ('Cancelled', 'Template')
                AND (
                    (
                        t.exp_start_date IS NOT NULL
                        AND t.exp_end_date IS NOT NULL
                        AND DATE(t.exp_start_date) < %(next_month_start)s
                        AND DATE(t.exp_end_date) >= %(month_start)s
                    )
                    OR (
                        t.status = 'Completed'
                        AND t.completed_on IS NOT NULL
                        AND t.completed_on >= %(month_start)s
                        AND t.completed_on < %(next_month_start)s
                    )
                    OR (
                        t.status NOT IN ('Completed', 'Cancelled', 'Template')
                        AND t.exp_end_date IS NOT NULL
                        AND DATE(t.exp_end_date) < %(month_start)s
                    )
                )
            ORDER BY
                CASE
                    WHEN
                        t.status NOT IN ('Completed', 'Cancelled', 'Template')
                        AND t.exp_end_date IS NOT NULL
                        AND DATE(t.exp_end_date) < %(today)s
                    THEN 1
                    WHEN t.priority = 'Urgent' THEN 2
                    WHEN
                        t.status NOT IN ('Completed', 'Cancelled', 'Template')
                        AND t.exp_end_date IS NOT NULL
                        AND DATE(t.exp_end_date) >= %(today)s
                        AND DATE(t.exp_end_date) <= %(due_soon_end)s
                    THEN 3
                    WHEN t.priority = 'High' THEN 4
                    WHEN t.status = 'Pending Review' THEN 5
                    WHEN t.status = 'Working' THEN 6
                    WHEN t.status = 'Open' THEN 7
                    WHEN t.status = 'Completed' THEN 8
                    ELSE 9
                END,
                t.exp_end_date ASC,
                t.subject ASC
            """,
            values={
                "employee": employee_id,
                "today": today,
                "month_start": month_start,
                "next_month_start": next_month_start,
                "due_soon_end": due_soon_end
            },
            as_dict=True
        )

        # -----------------------------------------------------
        # Normal main-task summaries
        # Shown separately and excluded from workload totals.
        # -----------------------------------------------------

        main_tasks = frappe.db.sql(
            """
            SELECT
                t.name AS task,
                t.subject AS subject,
                t.project AS project,
                IFNULL(p.project_name, '') AS project_name,
                t.status AS status,
                t.priority AS priority,
                IFNULL(t.progress, 0) AS progress,
                IFNULL(t.expected_time, 0) AS expected_time,
                IFNULL(t.actual_time, 0) AS actual_time,
                IFNULL(t.custom_child_task_count, 0) AS child_task_count,
                IFNULL(
                    t.custom_completed_child_task_count,
                    0
                ) AS completed_child_task_count,
                IFNULL(
                    t.custom_parent_rollup_locked,
                    0
                ) AS parent_rollup_locked,
                t.exp_end_date AS exp_end_date,
                t.completed_on AS completed_on,
                CASE
                    WHEN
                        t.status NOT IN ('Completed', 'Cancelled', 'Template')
                        AND t.exp_end_date IS NOT NULL
                        AND DATE(t.exp_end_date) < %(today)s
                    THEN 1 ELSE 0
                END AS is_overdue
            FROM `tabTask` t
            LEFT JOIN `tabProject` p
                ON p.name = t.project
            WHERE
                t.custom_assign_to = %(employee)s
                AND IFNULL(t.is_template, 0) = 0
                AND IFNULL(t.is_group, 0) = 1
                AND IFNULL(t.custom_project_workplan, 0) = 0
                AND IFNULL(t.custom_child_task_count, 0) > 0
                AND t.status NOT IN ('Cancelled', 'Template')
                AND (
                    t.status NOT IN ('Completed', 'Cancelled', 'Template')
                    OR (
                        t.status = 'Completed'
                        AND t.completed_on IS NOT NULL
                        AND t.completed_on >= %(month_start)s
                        AND t.completed_on < %(next_month_start)s
                    )
                )
            ORDER BY
                CASE
                    WHEN
                        t.status NOT IN ('Completed', 'Cancelled', 'Template')
                        AND t.exp_end_date IS NOT NULL
                        AND DATE(t.exp_end_date) < %(today)s
                    THEN 1
                    WHEN t.priority = 'Urgent' THEN 2
                    WHEN t.priority = 'High' THEN 3
                    WHEN t.status = 'Working' THEN 4
                    WHEN t.status = 'Open' THEN 5
                    WHEN t.status = 'Completed' THEN 6
                    ELSE 7
                END,
                t.exp_end_date ASC,
                t.subject ASC
            """,
            values={
                "employee": employee_id,
                "today": today,
                "month_start": month_start,
                "next_month_start": next_month_start
            },
            as_dict=True
        )

        if not tasks and not main_tasks:
            continue

        # -----------------------------------------------------
        # Operational counters
        # -----------------------------------------------------

        operational_task_count = len(tasks)
        main_task_count = len(main_tasks)
        open_tasks = 0
        working_tasks = 0
        pending_review_tasks = 0
        overdue_tasks = 0
        due_soon_tasks = 0
        completed_this_month = 0
        carried_forward_tasks = 0
        urgent_tasks = 0
        high_priority_tasks = 0
        expected_hours = 0.0
        actual_hours = 0.0
        active_progress_total = 0.0
        active_progress_count = 0
        attention_tasks = []
        current_tasks = []
        completed_tasks_list = []

        for task in tasks:
            task_status = task.get("status") or "Open"
            task_priority = task.get("priority") or ""
            task_progress = float(task.get("progress") or 0)
            task_expected_hours = float(task.get("expected_time") or 0)
            task_actual_hours = float(task.get("actual_time") or 0)
            is_overdue = int(task.get("is_overdue") or 0)
            is_due_soon = int(task.get("is_due_soon") or 0)
            is_carried_forward = int(task.get("is_carried_forward") or 0)

            expected_hours = expected_hours + task_expected_hours
            actual_hours = actual_hours + task_actual_hours

            if task_status == "Completed":
                completed_this_month = completed_this_month + 1
                completed_tasks_list.append(task)
                continue

            active_progress_total = active_progress_total + task_progress
            active_progress_count = active_progress_count + 1

            if task_status == "Open":
                open_tasks = open_tasks + 1
            elif task_status == "Working":
                working_tasks = working_tasks + 1
            elif task_status == "Pending Review":
                pending_review_tasks = pending_review_tasks + 1

            if is_overdue:
                overdue_tasks = overdue_tasks + 1
            if is_due_soon:
                due_soon_tasks = due_soon_tasks + 1
            if is_carried_forward:
                carried_forward_tasks = carried_forward_tasks + 1

            if task_priority == "Urgent":
                urgent_tasks = urgent_tasks + 1
            elif task_priority == "High":
                high_priority_tasks = high_priority_tasks + 1

            if (
                is_overdue
                or is_due_soon
                or is_carried_forward
                or task_priority == "Urgent"
            ):
                attention_tasks.append(task)
            else:
                current_tasks.append(task)

        average_progress = 0.0

        if active_progress_count > 0:
            average_progress = round(
                active_progress_total / active_progress_count,
                1
            )

        # -----------------------------------------------------
        # Safe display values and subject
        # -----------------------------------------------------

        safe_employee_name = frappe.utils.escape_html(employee_name)
        safe_department = frappe.utils.escape_html(department)
        safe_designation = frappe.utils.escape_html(designation)
        report_date = frappe.utils.formatdate(today, "dd MMMM yyyy")
        month_name = frappe.utils.formatdate(today, "MMMM yyyy")

        subject_template = settings.summary_email_subject or "Task Summary | {employee_name} | {report_date}"
        email_subject = subject_template.format(
            employee_name=employee_name,
            report_date=report_date,
            frequency=settings.summary_frequency or "Weekly",
        )

        # -----------------------------------------------------
        # Email header and KPI cards
        # -----------------------------------------------------

        message = (
            '<div style="max-width:1000px;margin:0 auto;padding:20px;'
            'background:#f4f7fb;color:#1f2937;font-family:Arial,Helvetica,'
            'sans-serif;direction:ltr;">'
            '<div style="padding:24px;border-radius:12px 12px 0 0;'
            'background:#17365d;color:#ffffff;">'
            '<table role="presentation" cellpadding="0" cellspacing="0" '
            'border="0" style="width:100%;border-collapse:collapse;"><tr>'
            '<td style="padding:0;color:#ffffff;text-align:left;vertical-align:'
            'middle;"><div style="font-size:22px;font-weight:700;">'
            'Task Summary</div><div style="margin-top:6px;font-size:'
            '14px;opacity:.92;">' + safe_employee_name + '</div><div style="'
            'margin-top:4px;font-size:12px;opacity:.82;">' + safe_designation
        )

        if designation and department:
            message = message + " | "

        message = (
            message + safe_department + '</div><div style="margin-top:8px;'
            'font-size:12px;opacity:.82;">Reporting Period: ' +
            frappe.utils.escape_html(month_name) +
            '&nbsp; | &nbsp;Report Date: ' +
            frappe.utils.escape_html(report_date) +
            '</div></td><td style="width:190px;padding:0 0 0 20px;'
            'text-align:right;vertical-align:middle;">' +
            company_logo_html +
            '</td></tr></table></div><div style="padding:22px;border:1px '
            'solid #dfe6ef;border-top:0;background:#ffffff;">'
            '<p style="margin-top:0;font-size:14px;line-height:1.7;">Dear ' +
            safe_employee_name + ',<br><br>Please find below your scheduled task '
            'summary. Operational task indicators are calculated from leaf '
            'tasks only. Main tasks are shown separately to avoid counting '
            'child-task progress and hours twice.</p>'
            '<table role="presentation" style="width:100%;margin:18px 0;'
            'border-spacing:7px;table-layout:fixed;"><tr>'
        )

        kpi_items = [
            ["Operational Tasks", operational_task_count, "#2490ef", "#e8f3ff", "#0969da"],
            ["Main Tasks", main_task_count, "#0f766e", "#ccfbf1", "#0f766e"],
            ["Open", open_tasks, "#64748b", "#f1f5f9", "#334155"],
            ["Working", working_tasks, "#f59e0b", "#fff4d6", "#a15c00"],
            ["Pending Review", pending_review_tasks, "#9333ea", "#f3e8ff", "#7e22ce"],
            ["Due in Next 7 Days", due_soon_tasks, "#ea580c", "#fff7ed", "#c2410c"],
            ["Overdue", overdue_tasks, "#dc2626", "#ffe7e7", "#c92a2a"],
            ["Completed This Month", completed_this_month, "#16a34a", "#dcfce7", "#15803d"]
        ]

        kpi_index = 0

        for kpi in kpi_items:
            if kpi_index == 4:
                message = message + "</tr><tr>"

            message = (
                message + '<td style="padding:14px;border-left:4px solid ' +
                kpi[2] + ';border-radius:8px;background:' + kpi[3] +
                ';vertical-align:top;"><div style="color:#475569;font-size:'
                '11px;">' + kpi[0] + '</div><div style="margin-top:4px;color:' +
                kpi[4] + ';font-size:23px;font-weight:700;">' +
                str(kpi[1]) + '</div></td>'
            )

            kpi_index = kpi_index + 1

        message = (
            message + '</tr></table><div style="margin-bottom:20px;padding:'
            '13px 15px;border:1px solid #e2e8f0;border-radius:8px;'
            'background:#f8fafc;color:#334155;font-size:12px;line-height:1.8;">'
            '<strong>Urgent Tasks:</strong> ' + str(urgent_tasks) +
            '&nbsp;&nbsp; | &nbsp;&nbsp;<strong>High Priority Tasks:</strong> ' +
            str(high_priority_tasks) +
            '&nbsp;&nbsp; | &nbsp;&nbsp;<strong>Average Active Progress:</strong> ' +
            str(average_progress) + '%<br><strong>Expected Operational Hours:'
            '</strong> ' + str(round(expected_hours, 2)) +
            '&nbsp;&nbsp; | &nbsp;&nbsp;<strong>Actual Operational Hours:</strong> ' +
            str(round(actual_hours, 2)) +
            '&nbsp;&nbsp; | &nbsp;&nbsp;<strong>Carried Forward:</strong> ' +
            str(carried_forward_tasks) + '</div>'
        )

        # -----------------------------------------------------
        # Attention-required operational tasks
        # -----------------------------------------------------

        if attention_tasks:
            message = (
                message + '<div style="margin:22px 0 10px;color:#b91c1c;'
                'font-size:17px;font-weight:700;">Attention Required</div>'
                '<div style="margin-bottom:10px;color:#64748b;font-size:12px;'
                'line-height:1.6;">Overdue, urgent, carried-forward, and tasks '
                'due within the next seven days.</div><table style="width:100%;'
                'margin-bottom:24px;border-collapse:collapse;font-size:12px;">'
                '<thead><tr style="background:#fee2e2;color:#7f1d1d;">'
                '<th style="padding:9px;border:1px solid #fecaca;text-align:left;">Task</th>'
                '<th style="padding:9px;border:1px solid #fecaca;text-align:left;">Project</th>'
                '<th style="padding:9px;border:1px solid #fecaca;text-align:left;">Status</th>'
                '<th style="padding:9px;border:1px solid #fecaca;text-align:left;">Priority</th>'
                '<th style="padding:9px;border:1px solid #fecaca;text-align:left;">Due Date</th>'
                '<th style="padding:9px;border:1px solid #fecaca;text-align:center;">Delay Days</th>'
                '<th style="padding:9px;border:1px solid #fecaca;text-align:center;">Progress</th>'
                '</tr></thead><tbody>'
            )

            for task in attention_tasks:
                task_name = task.get("task") or ""
                task_subject = task.get("subject") or task_name
                project_code = task.get("project") or ""
                project_name = task.get("project_name") or ""
                project_display = project_code

                if project_name and project_name != project_code:
                    project_display = project_code + " | " + project_name

                task_priority = task.get("priority") or ""
                task_status = task.get("status") or "Open"
                task_progress = task.get("progress") or 0
                delay_days = task.get("delay_days") or 0
                is_overdue = int(task.get("is_overdue") or 0)
                is_due_soon = int(task.get("is_due_soon") or 0)
                is_carried_forward = int(task.get("is_carried_forward") or 0)
                display_status = task_status

                if is_overdue and is_carried_forward:
                    display_status = "Overdue / Carried Forward"
                elif is_overdue:
                    display_status = "Overdue"
                elif is_carried_forward:
                    display_status = "Carried Forward"
                elif is_due_soon:
                    display_status = "Due Soon"

                due_date_text = ""

                if task.get("exp_end_date"):
                    due_date_text = frappe.utils.formatdate(
                        task.get("exp_end_date"),
                        "dd MMM yyyy"
                    )

                task_url = site_url + "/app/task/" + task_name
                task_link = (
                    '<a href="' + frappe.utils.escape_html(task_url) +
                    '" target="_blank" rel="noopener noreferrer" style="color:'
                    '#0969da;font-weight:600;text-decoration:underline;">' +
                    frappe.utils.escape_html(task_subject) + '</a>'
                )

                message = (
                    message + '<tr><td style="padding:9px;border:1px solid '
                    '#e5e7eb;vertical-align:top;">' + task_link + '</td><td '
                    'style="padding:9px;border:1px solid #e5e7eb;vertical-align:'
                    'top;">' + frappe.utils.escape_html(project_display) +
                    '</td><td style="padding:9px;border:1px solid #e5e7eb;'
                    'vertical-align:top;">' +
                    frappe.utils.escape_html(display_status) + '</td><td style="'
                    'padding:9px;border:1px solid #e5e7eb;vertical-align:top;">' +
                    frappe.utils.escape_html(task_priority) + '</td><td style="'
                    'padding:9px;border:1px solid #e5e7eb;white-space:nowrap;">' +
                    frappe.utils.escape_html(due_date_text) + '</td><td style="'
                    'padding:9px;border:1px solid #e5e7eb;color:#b91c1c;'
                    'font-weight:700;text-align:center;">' + str(delay_days) +
                    '</td><td style="padding:9px;border:1px solid #e5e7eb;'
                    'font-weight:600;text-align:center;">' + str(task_progress) +
                    '%</td></tr>'
                )

            message = message + "</tbody></table>"

        # -----------------------------------------------------
        # Current operational tasks
        # -----------------------------------------------------

        if current_tasks:
            message = (
                message + '<div style="margin:22px 0 10px;color:#17365d;'
                'font-size:17px;font-weight:700;">Current Active Tasks</div>'
                '<table style="width:100%;margin-bottom:24px;border-collapse:'
                'collapse;font-size:12px;"><thead><tr style="background:#e8f3ff;'
                'color:#17365d;"><th style="padding:9px;border:1px solid #cbd5e1;'
                'text-align:left;">Task</th><th style="padding:9px;border:1px '
                'solid #cbd5e1;text-align:left;">Project</th><th style="padding:'
                '9px;border:1px solid #cbd5e1;text-align:left;">Status</th><th '
                'style="padding:9px;border:1px solid #cbd5e1;text-align:left;">'
                'Priority</th><th style="padding:9px;border:1px solid #cbd5e1;'
                'text-align:left;">Due Date</th><th style="padding:9px;border:'
                '1px solid #cbd5e1;text-align:center;">Expected Hours</th><th '
                'style="padding:9px;border:1px solid #cbd5e1;text-align:center;">'
                'Progress</th></tr></thead><tbody>'
            )

            for task in current_tasks:
                task_name = task.get("task") or ""
                task_subject = task.get("subject") or task_name
                project_code = task.get("project") or ""
                project_name = task.get("project_name") or ""
                project_display = project_code

                if project_name and project_name != project_code:
                    project_display = project_code + " | " + project_name

                due_date_text = ""

                if task.get("exp_end_date"):
                    due_date_text = frappe.utils.formatdate(
                        task.get("exp_end_date"),
                        "dd MMM yyyy"
                    )

                task_url = site_url + "/app/task/" + task_name
                task_link = (
                    '<a href="' + frappe.utils.escape_html(task_url) +
                    '" target="_blank" rel="noopener noreferrer" style="color:'
                    '#0969da;font-weight:600;text-decoration:underline;">' +
                    frappe.utils.escape_html(task_subject) + '</a>'
                )

                message = (
                    message + '<tr><td style="padding:9px;border:1px solid '
                    '#e5e7eb;">' + task_link + '</td><td style="padding:9px;'
                    'border:1px solid #e5e7eb;">' +
                    frappe.utils.escape_html(project_display) + '</td><td style="'
                    'padding:9px;border:1px solid #e5e7eb;">' +
                    frappe.utils.escape_html(task.get("status") or "Open") +
                    '</td><td style="padding:9px;border:1px solid #e5e7eb;">' +
                    frappe.utils.escape_html(task.get("priority") or "") +
                    '</td><td style="padding:9px;border:1px solid #e5e7eb;'
                    'white-space:nowrap;">' +
                    frappe.utils.escape_html(due_date_text) + '</td><td style="'
                    'padding:9px;border:1px solid #e5e7eb;text-align:center;">' +
                    str(task.get("expected_time") or 0) + '</td><td style="'
                    'padding:9px;border:1px solid #e5e7eb;text-align:center;'
                    'font-weight:600;">' + str(task.get("progress") or 0) +
                    '%</td></tr>'
                )

            message = message + "</tbody></table>"

        # -----------------------------------------------------
        # Main task summaries - no double counting in KPIs
        # -----------------------------------------------------

        if main_tasks:
            message = (
                message + '<div style="margin:22px 0 10px;color:#0f766e;'
                'font-size:17px;font-weight:700;">Main Task Summaries</div>'
                '<div style="margin-bottom:10px;color:#64748b;font-size:12px;'
                'line-height:1.6;">These values are calculated from child tasks '
                'and are displayed for reference only. They are not added again '
                'to operational hour or progress totals.</div><table style="width:'
                '100%;margin-bottom:24px;border-collapse:collapse;font-size:12px;">'
                '<thead><tr style="background:#ccfbf1;color:#115e59;">'
                '<th style="padding:9px;border:1px solid #99f6e4;text-align:left;">Main Task</th>'
                '<th style="padding:9px;border:1px solid #99f6e4;text-align:left;">Project</th>'
                '<th style="padding:9px;border:1px solid #99f6e4;text-align:left;">Status</th>'
                '<th style="padding:9px;border:1px solid #99f6e4;text-align:center;">Child Tasks</th>'
                '<th style="padding:9px;border:1px solid #99f6e4;text-align:center;">Completed</th>'
                '<th style="padding:9px;border:1px solid #99f6e4;text-align:center;">Remaining</th>'
                '<th style="padding:9px;border:1px solid #99f6e4;text-align:center;">Progress</th>'
                '<th style="padding:9px;border:1px solid #99f6e4;text-align:center;">Expected Hours</th>'
                '<th style="padding:9px;border:1px solid #99f6e4;text-align:center;">Actual Hours</th>'
                '</tr></thead><tbody>'
            )

            for main_task in main_tasks:
                task_name = main_task.get("task") or ""
                task_subject = main_task.get("subject") or task_name
                project_code = main_task.get("project") or ""
                project_name = main_task.get("project_name") or ""
                project_display = project_code

                if project_name and project_name != project_code:
                    project_display = project_code + " | " + project_name

                child_count = int(main_task.get("child_task_count") or 0)
                completed_child_count = int(
                    main_task.get("completed_child_task_count") or 0
                )
                remaining_child_count = child_count - completed_child_count

                if remaining_child_count < 0:
                    remaining_child_count = 0

                display_status = main_task.get("status") or "Open"

                if int(main_task.get("is_overdue") or 0):
                    display_status = "Overdue"

                task_url = site_url + "/app/task/" + task_name
                task_link = (
                    '<a href="' + frappe.utils.escape_html(task_url) +
                    '" target="_blank" rel="noopener noreferrer" style="color:'
                    '#0f766e;font-weight:600;text-decoration:underline;">' +
                    frappe.utils.escape_html(task_subject) + '</a>'
                )

                message = (
                    message + '<tr><td style="padding:9px;border:1px solid '
                    '#e5e7eb;">' + task_link + '</td><td style="padding:9px;'
                    'border:1px solid #e5e7eb;">' +
                    frappe.utils.escape_html(project_display) + '</td><td style="'
                    'padding:9px;border:1px solid #e5e7eb;">' +
                    frappe.utils.escape_html(display_status) + '</td><td style="'
                    'padding:9px;border:1px solid #e5e7eb;text-align:center;">' +
                    str(child_count) + '</td><td style="padding:9px;border:1px '
                    'solid #e5e7eb;text-align:center;">' +
                    str(completed_child_count) + '</td><td style="padding:9px;'
                    'border:1px solid #e5e7eb;text-align:center;">' +
                    str(remaining_child_count) + '</td><td style="padding:9px;'
                    'border:1px solid #e5e7eb;text-align:center;font-weight:600;">' +
                    str(main_task.get("progress") or 0) + '%</td><td style="'
                    'padding:9px;border:1px solid #e5e7eb;text-align:center;">' +
                    str(main_task.get("expected_time") or 0) + '</td><td style="'
                    'padding:9px;border:1px solid #e5e7eb;text-align:center;">' +
                    str(main_task.get("actual_time") or 0) + '</td></tr>'
                )

            message = message + "</tbody></table>"

        # -----------------------------------------------------
        # Completed operational tasks this month
        # -----------------------------------------------------

        if completed_tasks_list:
            message = (
                message + '<div style="margin:22px 0 10px;color:#15803d;'
                'font-size:17px;font-weight:700;">Completed This Month</div>'
                '<table style="width:100%;margin-bottom:24px;border-collapse:'
                'collapse;font-size:12px;"><thead><tr style="background:#dcfce7;'
                'color:#166534;"><th style="padding:9px;border:1px solid #bbf7d0;'
                'text-align:left;">Task</th><th style="padding:9px;border:1px '
                'solid #bbf7d0;text-align:left;">Project</th><th style="padding:'
                '9px;border:1px solid #bbf7d0;text-align:left;">Priority</th><th '
                'style="padding:9px;border:1px solid #bbf7d0;text-align:left;">'
                'Completed On</th><th style="padding:9px;border:1px solid #bbf7d0;'
                'text-align:center;">Expected Hours</th><th style="padding:9px;'
                'border:1px solid #bbf7d0;text-align:center;">Actual Hours</th>'
                '</tr></thead><tbody>'
            )

            for task in completed_tasks_list:
                task_name = task.get("task") or ""
                task_subject = task.get("subject") or task_name
                project_code = task.get("project") or ""
                project_name = task.get("project_name") or ""
                project_display = project_code

                if project_name and project_name != project_code:
                    project_display = project_code + " | " + project_name

                completed_on_text = ""

                if task.get("completed_on"):
                    completed_on_text = frappe.utils.formatdate(
                        task.get("completed_on"),
                        "dd MMM yyyy"
                    )

                task_url = site_url + "/app/task/" + task_name
                task_link = (
                    '<a href="' + frappe.utils.escape_html(task_url) +
                    '" target="_blank" rel="noopener noreferrer" style="color:'
                    '#0969da;font-weight:600;text-decoration:underline;">' +
                    frappe.utils.escape_html(task_subject) + '</a>'
                )

                message = (
                    message + '<tr><td style="padding:9px;border:1px solid '
                    '#e5e7eb;">' + task_link + '</td><td style="padding:9px;'
                    'border:1px solid #e5e7eb;">' +
                    frappe.utils.escape_html(project_display) + '</td><td style="'
                    'padding:9px;border:1px solid #e5e7eb;">' +
                    frappe.utils.escape_html(task.get("priority") or "") +
                    '</td><td style="padding:9px;border:1px solid #e5e7eb;'
                    'white-space:nowrap;">' +
                    frappe.utils.escape_html(completed_on_text) + '</td><td '
                    'style="padding:9px;border:1px solid #e5e7eb;text-align:'
                    'center;">' + str(task.get("expected_time") or 0) +
                    '</td><td style="padding:9px;border:1px solid #e5e7eb;'
                    'text-align:center;">' + str(task.get("actual_time") or 0) +
                    '</td></tr>'
                )

            message = message + "</tbody></table>"

        # -----------------------------------------------------
        # Report link and closing
        # -----------------------------------------------------

        report_url = (
            site_url +
            "/app/query-report/Employees%20Task%20Tracker" +
            "?employee=" +
            employee_id +
            "&workplan_filter=Regular%20Tasks%20Only"
        )

        report_button = (
            '<a href="' + frappe.utils.escape_html(report_url) +
            '" target="_blank" rel="noopener noreferrer" style="display:'
            'inline-block;padding:12px 24px;border:1px solid #17365d;'
            'border-radius:7px;background-color:#17365d;color:#ffffff!important;'
            'font-size:13px;font-weight:700;text-decoration:none!important;">'
            'Open Employees Task Tracker</a>'
        )

        message = (
            message + '<div style="margin-top:18px;padding:14px 16px;'
            'border-left:4px solid #f59e0b;border-radius:8px;background:#fff7ed;'
            'color:#7c2d12;font-size:13px;line-height:1.7;"><strong>Required '
            'Action:</strong><br>Please review your assigned operational tasks '
            'and update their status, progress, expected hours, and completion '
            'information where necessary. Main-task summaries update from child '
            'tasks automatically.</div><div style="margin-top:22px;text-align:'
            'center;">' + report_button + '</div><div style="margin-top:24px;'
            'padding-top:14px;border-top:1px solid #e5e7eb;color:#64748b;'
            'font-size:12px;line-height:1.6;">Regards,<br>' +
            management_signature + '</div></div><div style="padding:13px;'
            'border-radius:0 0 12px 12px;background:#e9eef5;color:#64748b;'
            'text-align:center;font-size:11px;line-height:1.5;">This is an '
            'automated task summary generated by ERP System. Please do '
            'not reply directly to this email.</div></div>'
        )

        # -----------------------------------------------------
        # Queue email
        # -----------------------------------------------------

        recipients = list(dict.fromkeys(([recipient_email] if int(settings.summary_send_to_employees or 0) else []) + additional_recipients))
        if not recipients:
            continue
        if settings.summary_email_template:
            template = frappe.get_doc("Email Template", settings.summary_email_template)
            email_subject = frappe.render_template(template.subject or email_subject, {"employee": employee, "report_date": report_date, "frequency": settings.summary_frequency})
            message = frappe.render_template(template.response_html or template.response or message, {"employee": employee, "report_date": report_date, "frequency": settings.summary_frequency, "report_url": report_url})

        frappe.sendmail(
            recipients=recipients,
            subject=email_subject,
            message=message,
            reference_doctype="Employee",
            reference_name=employee_id,
            delayed=True
        )
        sent_count += 1

    return {"sent": sent_count, "additional_recipients": len(additional_recipients)}



WEEKDAYS = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}


def _period_key(settings, current):
    frequency = settings.summary_frequency or "Weekly"
    if frequency == "Daily":
        return current.strftime("D:%Y-%m-%d")
    if frequency == "Monthly":
        return current.strftime("M:%Y-%m")
    year, week, _ = current.isocalendar()
    return f"W:{year}-{week:02d}"


def _is_due(settings, current):
    if not int(settings.summary_schedule_enabled or 0):
        return False
    send_time = str(settings.summary_send_time or "08:00:00")[:5]
    if current.strftime("%H:%M") < send_time:
        return False
    if settings.summary_frequency == "Weekly" and current.weekday() != WEEKDAYS.get(settings.summary_weekly_day, 6):
        return False
    if settings.summary_frequency == "Monthly" and current.day != int(settings.summary_monthly_day or 1):
        return False
    return True


def get_next_send_datetime(settings=None, current=None):
    from datetime import datetime, timedelta

    settings = settings or get_settings()
    current = current or frappe.utils.get_datetime(frappe.utils.now())
    send_time = str(settings.summary_send_time or "08:00:00").split(":")
    hour = int(send_time[0] or 0)
    minute = int(send_time[1] or 0) if len(send_time) > 1 else 0
    candidate = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    frequency = settings.summary_frequency or "Weekly"

    if frequency == "Daily":
        if candidate <= current:
            candidate += timedelta(days=1)
        return candidate

    if frequency == "Weekly":
        target = WEEKDAYS.get(settings.summary_weekly_day, 6)
        candidate += timedelta(days=(target - candidate.weekday()) % 7)
        if candidate <= current:
            candidate += timedelta(days=7)
        return candidate

    day = max(1, min(28, int(settings.summary_monthly_day or 1)))
    candidate = candidate.replace(day=day)
    if candidate <= current:
        year = candidate.year + (1 if candidate.month == 12 else 0)
        month = 1 if candidate.month == 12 else candidate.month + 1
        candidate = candidate.replace(year=year, month=month, day=day)
    return candidate


def run_scheduled_task_summary():
    settings = get_settings()
    current = frappe.utils.get_datetime(frappe.utils.now())
    key = _period_key(settings, current)
    if not _is_due(settings, current) or settings.get("summary_last_period_key") == key:
        return {"sent": 0, "due": False, "period_key": key}
    return _run_and_record(key, manual=False)


@frappe.whitelist()
def send_task_summary_now():
    settings = get_settings()
    if frappe.session.user != "Administrator" and settings.administrative_role not in frappe.get_roles():
        frappe.throw("Only Task Management Administrators can send the summary manually.")
    return _run_and_record("MANUAL:" + frappe.utils.now_datetime().strftime("%Y%m%d%H%M%S"), manual=True)


def _run_and_record(period_key, manual=False):
    try:
        result = send_employee_task_summary(force=True) or {}
        values = {
            "summary_last_sent_on": frappe.utils.now(),
            "summary_last_send_status": "Completed",
            "summary_last_send_summary": frappe.as_json(result),
            "summary_next_send_on": get_next_send_datetime(),
        }
        if not manual:
            values["summary_last_period_key"] = period_key
        for field, value in values.items():
            frappe.db.set_single_value("Task Management Settings", field, value)
        frappe.db.commit()
        return result
    except Exception:
        error = frappe.get_traceback()
        frappe.db.set_single_value("Task Management Settings", "summary_last_send_status", "Failed")
        frappe.db.set_single_value("Task Management Settings", "summary_last_send_summary", error)
        frappe.log_error(error, "Scheduled Task Summary")
        raise


def weekly_employee_task_summary():
    """Backward-compatible entry point."""
    return run_scheduled_task_summary()
