from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
    # Employees Task Tracker v3.3 - Virtual Parent for Standalone Tasks
    # Frappe / ERPNext 16 Safe Execution Script Report
    # This report supports task follow-up and workload visibility. It does not rank or score employees.
    filters = frappe._dict(filters or {})
    view = filters.get("view") or "Operational Overview"
    today = frappe.utils.nowdate()

    # Normalize MultiSelectList values.
    selected = {}
    for key in ["companies","departments","branches","employees","projects","task_types","statuses","priorities","due_buckets","assignment_types"]:
        raw = filters.get(key)
        vals = []
        if isinstance(raw, list):
            for item in raw:
                val = item.get("value") if isinstance(item, dict) else item
                if val and str(val) not in vals:
                    vals.append(str(val))
        elif raw:
            for item in str(raw).split(","):
                val = item.strip()
                if val and val not in vals:
                    vals.append(val)
        selected[key] = vals

    meta = frappe.get_meta("Task")
    layout_types = ["Table","Table MultiSelect","Section Break","Column Break","Tab Break","HTML","Button","Heading","Fold"]
    fields = ["name","owner","subject","status","priority","progress","project","type","department","company","exp_start_date","exp_end_date","expected_time","actual_time","parent_task","is_group","is_milestone","is_template","completed_on","completed_by","review_date","closing_date","creation","modified"]
    for f in ["custom_assign_to","custom_task_assigned_by","custom_project_workplan","custom_expected_days","custom_self_assigned","description"]:
        if meta.has_field(f):
            fd = meta.get_field(f)
            if fd and fd.fieldtype not in layout_types and int(fd.is_virtual or 0) == 0 and f not in fields:
                fields.append(f)

    base_filters = {"is_template":0}
    if selected.get("companies"):
        base_filters["company"] = ["in",selected.get("companies")]
    if selected.get("departments"):
        base_filters["department"] = ["in",selected.get("departments")]
    if selected.get("employees") and meta.has_field("custom_assign_to"):
        base_filters["custom_assign_to"] = ["in",selected.get("employees")]
    if selected.get("projects"):
        base_filters["project"] = ["in",selected.get("projects")]
    if selected.get("task_types"):
        base_filters["type"] = ["in",selected.get("task_types")]
    if selected.get("priorities"):
        base_filters["priority"] = ["in",selected.get("priorities")]

    # My Tasks Only. Resolve the Employee linked to the current user before loading Tasks.
    current_user = frappe.session.user or ""
    my_tasks_only = int(filters.get("my_tasks_only") or 0)
    current_employee = ""
    if my_tasks_only and current_user:
        employee_link_meta = frappe.get_meta("Employee")
        employee_user_field = ""
        if employee_link_meta.has_field("custom_user_id"):
            employee_user_field = "custom_user_id"
        elif employee_link_meta.has_field("user_id"):
            employee_user_field = "user_id"
        if employee_user_field:
            current_employee_rows = frappe.get_all(
                "Employee",
                filters={employee_user_field:current_user,"status":"Active"},
                fields=["name"],
                order_by="modified desc",
                limit_page_length=1
            )
            if current_employee_rows:
                current_employee = current_employee_rows[0].get("name") or ""
        if meta.has_field("custom_assign_to"):
            base_filters["custom_assign_to"] = current_employee if current_employee else "__NO_LINKED_EMPLOYEE__"
        else:
            base_filters["name"] = "__NO_TASK_RESULT__"

    # Task Year filter. The year is based on the expected due date (exp_end_date).
    # An empty value means All Years.
    selected_year = str(filters.get("task_year") or "").strip()
    if selected_year:
        year_start = selected_year + "-01-01"
        year_end = selected_year + "-12-31"
        base_filters["exp_end_date"] = ["between",[year_start,year_end]]

    # Incremental loading. Each click increases the cumulative number of records.
    records_per_page = int(filters.get("records_per_page") or 50)
    if records_per_page not in [50,100,200,500]:
        records_per_page = 50
    page_number = int(filters.get("page_number") or 1)
    if page_number < 1:
        page_number = 1
    records_to_load = page_number * records_per_page
    summary_view = view in ["Employee Workload","Department Workload","Project Workload"]

    # Load all database-filtered candidates first. Several report conditions are
    # calculated below in Python, so limiting here would produce false Load More
    # results and could omit valid records from detail and summary views.
    tasks = frappe.get_all(
        "Task",
        filters=base_filters,
        fields=fields,
        order_by="modified desc",
        limit_page_length=0
    )
    has_next_page = False
    # Resolve conditional opening rights without a query per result row.
    can_open_all_tasks = current_user == "Administrator"
    if current_user and not can_open_all_tasks:
        system_manager_rows = frappe.get_all(
            "Has Role",
            filters={"parent":current_user,"parenttype":"User","role":"System Manager"},
            fields=["name"],
            limit_page_length=1
        )
        if system_manager_rows:
            can_open_all_tasks = True
    permission_task_ids = []
    task_owner_map = {}
    for t in tasks:
        task_id = t.get("name")
        parent_id = t.get("parent_task")
        if task_id:
            if task_id not in permission_task_ids:
                permission_task_ids.append(task_id)
            task_owner_map[task_id] = t.get("owner") or ""
        if parent_id and parent_id not in permission_task_ids:
            permission_task_ids.append(parent_id)

    missing_owner_ids = []
    for task_id in permission_task_ids:
        if task_id not in task_owner_map:
            missing_owner_ids.append(task_id)
    if missing_owner_ids:
        parent_owner_rows = frappe.get_all("Task",filters={"name":["in",missing_owner_ids]},fields=["name","owner"],limit_page_length=0)
        for owner_row in parent_owner_rows:
            task_owner_map[owner_row.get("name")] = owner_row.get("owner") or ""

    shared_task_ids = []
    if current_user and permission_task_ids and not can_open_all_tasks:
        share_rows = frappe.get_all("DocShare",filters={"share_doctype":"Task","share_name":["in",permission_task_ids],"user":current_user,"read":1},fields=["share_name"],limit_page_length=0)
        for share_row in share_rows:
            shared_id = share_row.get("share_name")
            if shared_id and shared_id not in shared_task_ids:
                shared_task_ids.append(shared_id)

    # Employee display names.
    emp_names = {}
    emp_ids = []
    for t in tasks:
        for f in ["custom_assign_to","custom_task_assigned_by"]:
            val = t.get(f)
            if val and val not in emp_ids:
                emp_ids.append(val)
    if emp_ids:
        employee_meta = frappe.get_meta("Employee")
        employee_fields = ["name","employee_name","department","company","status"]
        employee_branch_field = ""
        for branch_field in ["branch","custom_branch","custom_office","custom_location"]:
            if employee_meta.has_field(branch_field):
                branch_def = employee_meta.get_field(branch_field)
                if branch_def and branch_def.fieldtype not in layout_types and int(branch_def.is_virtual or 0) == 0:
                    employee_branch_field = branch_field
                    employee_fields.append(branch_field)
                    break
        for e in frappe.get_all("Employee",filters={"name":["in",emp_ids]},fields=employee_fields,limit_page_length=0):
            emp_names[e.get("name")] = e
    else:
        employee_branch_field = ""

    # Project names.
    project_map = {}
    project_ids = []
    for t in tasks:
        project_id = t.get("project") or ""
        if project_id and project_id not in project_ids:
            project_ids.append(project_id)
    if project_ids:
        for prj in frappe.get_all("Project",filters={"name":["in",project_ids]},fields=["name","project_name","status"],limit_page_length=0):
            project_map[prj.get("name")] = prj

    rows = []
    for t in tasks:
        status = t.get("status") or "Open"
        completed_status = status in ["Completed","Cancelled","Template"]
        end_date = t.get("exp_end_date")
        start_date = t.get("exp_start_date")
        overdue = False
        delay_days = 0
        days_remaining = None
        if end_date:
            end_day = str(end_date)[:10]
            delta = frappe.utils.date_diff(today,end_day)
            if not completed_status and delta > 0:
                overdue = True
                delay_days = delta
            else:
                days_remaining = 0 - delta
        display_status = "Overdue" if overdue else status
        due_bucket = "No Due Date"
        if end_date:
            if overdue:
                due_bucket = "Overdue"
            elif completed_status:
                due_bucket = "Completed"
            elif days_remaining == 0:
                due_bucket = "Due Today"
            elif days_remaining is not None and days_remaining <= 3:
                due_bucket = "Due in 3 Days"
            elif days_remaining is not None and days_remaining <= 7:
                due_bucket = "Due in 7 Days"
            else:
                due_bucket = "Later"
        is_workplan = int(t.get("custom_project_workplan") or 0)
        is_group = int(t.get("is_group") or 0)
        task_level = "Sub Task" if t.get("parent_task") else "Main Task"
        assignment_type = "Self Assigned" if int(t.get("custom_self_assigned") or 0) == 1 else "Assigned"
        assignee_id = t.get("custom_assign_to") or ""
        branch = emp_names.get(assignee_id,{}).get(employee_branch_field) if employee_branch_field else ""
        expected = float(t.get("expected_time") or 0)
        actual = float(t.get("actual_time") or 0)
        hours_variance = round(actual-expected,2)
        progress = float(t.get("progress") or 0)
        quality = []
        if not t.get("custom_assign_to") and not is_workplan:
            quality.append("Missing Assignee")
        if not end_date and not is_workplan and not completed_status:
            quality.append("Missing Due Date")
        if start_date and end_date and str(start_date) > str(end_date):
            quality.append("Invalid Date Range")
        if progress >= 100 and status not in ["Completed","Cancelled"]:
            quality.append("100% Progress but Not Completed")
        if status == "Completed" and progress < 100:
            quality.append("Completed Below 100% Progress")
        if status == "Completed" and not t.get("completed_on"):
            quality.append("Completed Without Completion Date")
        if t.get("review_date") and status not in ["Pending Review","Completed","Cancelled"]:
            quality.append("Review Date with Non-review Status")

        include = True
        if selected.get("statuses") and display_status not in selected.get("statuses"):
            include = False
        if selected.get("due_buckets") and due_bucket not in selected.get("due_buckets"):
            include = False
        if selected.get("assignment_types") and assignment_type not in selected.get("assignment_types"):
            include = False
        if selected.get("branches") and (branch or "Unassigned") not in selected.get("branches"):
            include = False
        level_filter = filters.get("task_level") or ""
        if level_filter and task_level != level_filter:
            include = False
        workplan_filter = filters.get("workplan_filter") or ""
        if workplan_filter == "Project Workplans Only" and not is_workplan:
            include = False
        if workplan_filter == "Regular Tasks Only" and is_workplan:
            include = False
        if int(filters.get("include_group_tasks") or 0) != 1 and is_group and not is_workplan:
            include = False
        if int(filters.get("milestones_only") or 0) == 1 and int(t.get("is_milestone") or 0) != 1:
            include = False
        if int(filters.get("overdue_only") or 0) == 1 and not overdue:
            include = False
        if int(filters.get("due_soon_only") or 0) == 1 and due_bucket not in ["Due Today","Due in 3 Days","Due in 7 Days"]:
            include = False
        if int(filters.get("quality_exceptions_only") or 0) == 1 and not quality:
            include = False
        if view == "Project Workplans" and not is_workplan:
            include = False
        if view == "Overdue Tasks" and not overdue:
            include = False
        if view == "Due Soon" and due_bucket not in ["Due Today","Due in 3 Days","Due in 7 Days"]:
            include = False
        if view == "Pending Review" and display_status != "Pending Review":
            include = False
        if view == "Data Quality Exceptions" and not quality:
            include = False
        subject_filter = str(filters.get("subject") or "").lower()
        if subject_filter and subject_filter not in str(t.get("subject") or "").lower():
            include = False
        if filters.get("from_date") and (not start_date or str(start_date)[:10] < str(filters.get("from_date"))):
            include = False
        if filters.get("to_date") and (not end_date or str(end_date)[:10] > str(filters.get("to_date"))):
            include = False

        if include:
            task_id = t.get("name") or ""
            parent_task_id = t.get("parent_task") or ""
            can_open_task = 0
            can_open_parent_task = 0
            if can_open_all_tasks:
                can_open_task = 1
                if parent_task_id:
                    can_open_parent_task = 1
            else:
                if task_id and (task_owner_map.get(task_id) == current_user or task_id in shared_task_ids):
                    can_open_task = 1
                if parent_task_id and (task_owner_map.get(parent_task_id) == current_user or parent_task_id in shared_task_ids):
                    can_open_parent_task = 1
            assignee = t.get("custom_assign_to") or ""
            assigner = t.get("custom_task_assigned_by") or ""
            row = {"task":task_id,"can_open_task":can_open_task,"subject":t.get("subject") or "","project_workplan":is_workplan,"is_group":is_group,"task_level":task_level,"assigned_employee":assignee,"assigned_employee_name":emp_names.get(assignee,{}).get("employee_name") or assignee,"department":t.get("department") or emp_names.get(assignee,{}).get("department") or "","branch":branch or "","company":t.get("company") or emp_names.get(assignee,{}).get("company") or "","project":t.get("project") or "","project_name":project_map.get(t.get("project") or "",{}).get("project_name") or "","project_status":project_map.get(t.get("project") or "",{}).get("status") or "","task_type":t.get("type") or "","status":status,"display_status":display_status,"priority":t.get("priority") or "","progress":progress,"exp_start_date":start_date,"exp_end_date":end_date,"due_bucket":due_bucket,"days_remaining":days_remaining,"delay_days":delay_days,"expected_days":float(t.get("custom_expected_days") or 0),"expected_time":expected,"actual_time":actual,"hours_variance":hours_variance,"parent_task":parent_task_id,"can_open_parent_task":can_open_parent_task,"assigned_by":assigner,"assigned_by_name":emp_names.get(assigner,{}).get("employee_name") or assigner,"assignment_type":assignment_type,"is_milestone":int(t.get("is_milestone") or 0),"completed_on":t.get("completed_on"),"review_date":t.get("review_date"),"closing_date":t.get("closing_date"),"modified":t.get("modified"),"quality_flags":"; ".join(quality),"quality_issue_count":len(quality),"_context_companies":t.get("company") or "","_context_departments":t.get("department") or "","_context_branches":branch or "Unassigned","_context_employees":assignee,"_context_projects":t.get("project") or "","_context_task_types":t.get("type") or "","_context_statuses":display_status,"_context_priorities":t.get("priority") or "","_context_due_buckets":due_bucket,"_context_assignment_types":assignment_type}
            rows.append(row)

    # User-controlled organization and ordering.
    organize_by = filters.get("organize_by") or "Management Priority"
    secondary_sort = filters.get("secondary_sort") or "Due Date"
    show_group_column = int(filters.get("show_group_column") or 1)
    ordered = []
    for r in rows:
        rank = 10
        if r.get("display_status") == "Overdue": rank = 1
        elif r.get("priority") == "Urgent": rank = 2
        elif r.get("priority") == "High": rank = 3
        elif r.get("display_status") == "Pending Review": rank = 4
        elif r.get("due_bucket") in ["Due Today","Due in 3 Days","Due in 7 Days"]: rank = 5
        elif r.get("display_status") == "Working": rank = 6
        elif r.get("display_status") == "Open": rank = 7
        elif r.get("display_status") == "Completed": rank = 8
        elif r.get("display_status") == "Cancelled": rank = 9
        group_value = ""
        if organize_by == "Employee": group_value = r.get("assigned_employee_name") or "Unassigned"
        elif organize_by == "Department": group_value = r.get("department") or "Unassigned"
        elif organize_by == "Branch": group_value = r.get("branch") or "Unassigned"
        elif organize_by == "Task Type": group_value = r.get("task_type") or "Unassigned"
        elif organize_by == "Status": group_value = r.get("display_status") or "Unassigned"
        elif organize_by == "Priority": group_value = r.get("priority") or "Not Set"
        elif organize_by == "Project": group_value = r.get("project_name") or r.get("project") or "No Project"
        elif organize_by == "Parent Task": group_value = r.get("parent_task") or "Main Tasks"
        else: group_value = "Management Priority"
        r["organization_group"] = group_value
        if secondary_sort == "Employee": secondary = str(r.get("assigned_employee_name") or "")
        elif secondary_sort == "Department": secondary = str(r.get("department") or "")
        elif secondary_sort == "Task Type": secondary = str(r.get("task_type") or "")
        elif secondary_sort == "Priority": secondary = str(r.get("priority") or "")
        elif secondary_sort == "Progress": secondary = str(100000-float(r.get("progress") or 0)).zfill(12)
        elif secondary_sort == "Subject": secondary = str(r.get("subject") or "")
        else: secondary = str(r.get("exp_end_date") or "9999-12-31")
        primary = str(group_value or "") if organize_by != "Management Priority" else str(rank).zfill(2)
        rk = (primary,secondary,str(rank).zfill(2),str(r.get("subject") or ""))
        pos = 0
        inserted = False
        for e in ordered:
            erank = 10
            if e.get("display_status") == "Overdue": erank = 1
            elif e.get("priority") == "Urgent": erank = 2
            elif e.get("priority") == "High": erank = 3
            elif e.get("display_status") == "Pending Review": erank = 4
            elif e.get("due_bucket") in ["Due Today","Due in 3 Days","Due in 7 Days"]: erank = 5
            elif e.get("display_status") == "Working": erank = 6
            elif e.get("display_status") == "Open": erank = 7
            elif e.get("display_status") == "Completed": erank = 8
            elif e.get("display_status") == "Cancelled": erank = 9
            if secondary_sort == "Employee": esecond = str(e.get("assigned_employee_name") or "")
            elif secondary_sort == "Department": esecond = str(e.get("department") or "")
            elif secondary_sort == "Task Type": esecond = str(e.get("task_type") or "")
            elif secondary_sort == "Priority": esecond = str(e.get("priority") or "")
            elif secondary_sort == "Progress": esecond = str(100000-float(e.get("progress") or 0)).zfill(12)
            elif secondary_sort == "Subject": esecond = str(e.get("subject") or "")
            else: esecond = str(e.get("exp_end_date") or "9999-12-31")
            eprimary = str(e.get("organization_group") or "") if organize_by != "Management Priority" else str(erank).zfill(2)
            ek = (eprimary,esecond,str(erank).zfill(2),str(e.get("subject") or ""))
            if rk < ek:
                ordered.insert(pos,r)
                inserted = True
                break
            pos = pos + 1
        if not inserted:
            ordered.append(r)
    rows = ordered

    # Hierarchical Task organization.
    # When Parent Task is selected, tasks are displayed as a real multi-level tree.
    if organize_by == "Parent Task":
        hierarchy_row_map = {}
        hierarchy_task_order = []
        hierarchy_children_map = {}

        for hierarchy_row in rows:
            hierarchy_task_id = hierarchy_row.get("task") or ""
            if hierarchy_task_id:
                hierarchy_row_map[hierarchy_task_id] = hierarchy_row
                hierarchy_task_order.append(hierarchy_task_id)

        # Load every missing ancestor recursively. This is required because a parent
        # may be excluded by My Tasks, Employee, status, group-task, or date filters
        # while one or more visible descendants still match the active filters.
        hierarchy_pending_parent_ids = []
        for hierarchy_task_id in hierarchy_task_order:
            hierarchy_parent_id = hierarchy_row_map.get(hierarchy_task_id,{}).get("parent_task") or ""
            if hierarchy_parent_id and hierarchy_parent_id not in hierarchy_row_map and hierarchy_parent_id not in hierarchy_pending_parent_ids:
                hierarchy_pending_parent_ids.append(hierarchy_parent_id)

        hierarchy_guard = 0
        while hierarchy_pending_parent_ids and hierarchy_guard < 25:
            hierarchy_guard = hierarchy_guard + 1
            hierarchy_batch_ids = []
            for hierarchy_parent_id in hierarchy_pending_parent_ids:
                if hierarchy_parent_id and hierarchy_parent_id not in hierarchy_row_map and hierarchy_parent_id not in hierarchy_batch_ids:
                    hierarchy_batch_ids.append(hierarchy_parent_id)
            hierarchy_pending_parent_ids = []
            if not hierarchy_batch_ids:
                break

            hierarchy_parent_rows = frappe.get_all(
                "Task",
                filters={"name":["in",hierarchy_batch_ids]},
                fields=fields,
                limit_page_length=0
            )

            for hierarchy_parent in hierarchy_parent_rows:
                hierarchy_parent_task_id = hierarchy_parent.get("name") or ""
                if not hierarchy_parent_task_id or hierarchy_parent_task_id in hierarchy_row_map:
                    continue

                hierarchy_parent_of_parent = hierarchy_parent.get("parent_task") or ""
                hierarchy_assignee = hierarchy_parent.get("custom_assign_to") or ""
                hierarchy_assigner = hierarchy_parent.get("custom_task_assigned_by") or ""
                hierarchy_project = hierarchy_parent.get("project") or ""
                hierarchy_status = hierarchy_parent.get("status") or "Open"
                hierarchy_progress = float(hierarchy_parent.get("progress") or 0)
                hierarchy_expected = float(hierarchy_parent.get("expected_time") or 0)
                hierarchy_actual = float(hierarchy_parent.get("actual_time") or 0)
                hierarchy_is_workplan = int(hierarchy_parent.get("custom_project_workplan") or 0)
                hierarchy_is_group = int(hierarchy_parent.get("is_group") or 0)
                hierarchy_can_open = 0
                if can_open_all_tasks:
                    hierarchy_can_open = 1
                elif hierarchy_parent_task_id and (hierarchy_parent.get("owner") == current_user or hierarchy_parent_task_id in shared_task_ids):
                    hierarchy_can_open = 1

                hierarchy_project_name = project_map.get(hierarchy_project,{}).get("project_name") or hierarchy_project
                hierarchy_project_status = project_map.get(hierarchy_project,{}).get("status") or ""
                hierarchy_assignee_name = emp_names.get(hierarchy_assignee,{}).get("employee_name") or hierarchy_assignee
                hierarchy_assigner_name = emp_names.get(hierarchy_assigner,{}).get("employee_name") or hierarchy_assigner
                hierarchy_branch = emp_names.get(hierarchy_assignee,{}).get(employee_branch_field) if employee_branch_field else ""

                hierarchy_ancestor_row = {
                    "task":hierarchy_parent_task_id,"can_open_task":hierarchy_can_open,"subject":hierarchy_parent.get("subject") or "",
                    "project_workplan":hierarchy_is_workplan,"is_group":hierarchy_is_group,
                    "task_level":"Sub Task" if hierarchy_parent_of_parent else "Main Task",
                    "assigned_employee":hierarchy_assignee,"assigned_employee_name":hierarchy_assignee_name,
                    "department":hierarchy_parent.get("department") or emp_names.get(hierarchy_assignee,{}).get("department") or "",
                    "branch":hierarchy_branch or "","company":hierarchy_parent.get("company") or emp_names.get(hierarchy_assignee,{}).get("company") or "",
                    "project":hierarchy_project,"project_name":hierarchy_project_name,"project_status":hierarchy_project_status,
                    "task_type":hierarchy_parent.get("type") or "","status":hierarchy_status,"display_status":hierarchy_status,
                    "priority":hierarchy_parent.get("priority") or "","progress":hierarchy_progress,
                    "exp_start_date":hierarchy_parent.get("exp_start_date"),"exp_end_date":hierarchy_parent.get("exp_end_date"),
                    "due_bucket":"","days_remaining":None,"delay_days":0,
                    "expected_days":float(hierarchy_parent.get("custom_expected_days") or 0),
                    "expected_time":hierarchy_expected,"actual_time":hierarchy_actual,
                    "hours_variance":round(hierarchy_actual-hierarchy_expected,2),
                    "parent_task":hierarchy_parent_of_parent,"can_open_parent_task":0,
                    "assigned_by":hierarchy_assigner,"assigned_by_name":hierarchy_assigner_name,
                    "assignment_type":"Self Assigned" if int(hierarchy_parent.get("custom_self_assigned") or 0) == 1 else "Assigned",
                    "is_milestone":int(hierarchy_parent.get("is_milestone") or 0),
                    "completed_on":hierarchy_parent.get("completed_on"),"review_date":hierarchy_parent.get("review_date"),
                    "closing_date":hierarchy_parent.get("closing_date"),"modified":hierarchy_parent.get("modified"),
                    "quality_flags":"","quality_issue_count":0,"hierarchy_context_only":1
                }
                hierarchy_row_map[hierarchy_parent_task_id] = hierarchy_ancestor_row
                hierarchy_task_order.insert(0,hierarchy_parent_task_id)

                if hierarchy_parent_of_parent and hierarchy_parent_of_parent not in hierarchy_row_map and hierarchy_parent_of_parent not in hierarchy_pending_parent_ids:
                    hierarchy_pending_parent_ids.append(hierarchy_parent_of_parent)

        # Build the full parent-child map after all ancestors have been restored.
        hierarchy_roots = []
        hierarchy_standalone_tasks = []
        for hierarchy_task_id in hierarchy_task_order:
            hierarchy_row = hierarchy_row_map.get(hierarchy_task_id) or {}
            hierarchy_parent_id = hierarchy_row.get("parent_task") or ""
            hierarchy_is_group_root = int(hierarchy_row.get("is_group") or 0) == 1
            if hierarchy_parent_id and hierarchy_parent_id in hierarchy_row_map and hierarchy_parent_id != hierarchy_task_id:
                if hierarchy_parent_id not in hierarchy_children_map:
                    hierarchy_children_map[hierarchy_parent_id] = []
                if hierarchy_task_id not in hierarchy_children_map.get(hierarchy_parent_id):
                    hierarchy_children_map[hierarchy_parent_id].append(hierarchy_task_id)
            else:
                # Only Tasks explicitly marked as groups are treated as genuine main roots.
                # Unlinked non-group Tasks are collected in one standalone section.
                if hierarchy_is_group_root:
                    if hierarchy_task_id not in hierarchy_roots:
                        hierarchy_roots.append(hierarchy_task_id)
                elif hierarchy_task_id not in hierarchy_standalone_tasks:
                    hierarchy_standalone_tasks.append(hierarchy_task_id)

        hierarchy_ordered_rows = []
        hierarchy_visited = []
        hierarchy_root_sequence = 0

        for hierarchy_root_id in hierarchy_roots:
            if hierarchy_root_id in hierarchy_visited:
                continue
            hierarchy_root_sequence = hierarchy_root_sequence + 1
            hierarchy_stack = [{"task":hierarchy_root_id,"number":str(hierarchy_root_sequence),"depth":0,"root_task":hierarchy_root_id}]
            while hierarchy_stack:
                hierarchy_item = hierarchy_stack.pop()
                hierarchy_task_id = hierarchy_item.get("task") or ""
                if not hierarchy_task_id or hierarchy_task_id in hierarchy_visited:
                    continue
                hierarchy_row = hierarchy_row_map.get(hierarchy_task_id)
                if not hierarchy_row:
                    continue
                hierarchy_visited.append(hierarchy_task_id)
                hierarchy_number = hierarchy_item.get("number") or ""
                hierarchy_depth = int(hierarchy_item.get("depth") or 0)
                hierarchy_root_task = hierarchy_item.get("root_task") or hierarchy_task_id
                hierarchy_children = hierarchy_children_map.get(hierarchy_task_id) or []
                hierarchy_row["hierarchy_number"] = hierarchy_number
                hierarchy_row["hierarchy_depth"] = hierarchy_depth
                hierarchy_row["hierarchy_root_task"] = hierarchy_root_task
                hierarchy_row["hierarchy_has_children"] = 1 if hierarchy_children else 0
                hierarchy_row["organization_group"] = hierarchy_root_task
                hierarchy_row["organization_group_display"] = ""
                # A separator belongs only to the true root Task, never to nested parents or leaves.
                hierarchy_row["group_start"] = 1 if hierarchy_depth == 0 else 0
                hierarchy_row["group_sequence"] = hierarchy_root_sequence
                hierarchy_ordered_rows.append(hierarchy_row)
                hierarchy_child_position = len(hierarchy_children)
                while hierarchy_child_position > 0:
                    hierarchy_child_position = hierarchy_child_position - 1
                    hierarchy_child_id = hierarchy_children[hierarchy_child_position]
                    hierarchy_stack.append({"task":hierarchy_child_id,"number":hierarchy_number + "." + str(hierarchy_child_position + 1),"depth":hierarchy_depth + 1,"root_task":hierarchy_root_task})

        # Place all unlinked non-group Tasks under one virtual main classification.
        # The virtual row has no Task code and exists only to organize the report.
        if hierarchy_standalone_tasks:
            hierarchy_root_sequence = hierarchy_root_sequence + 1
            hierarchy_virtual_root_number = str(hierarchy_root_sequence)
            hierarchy_virtual_root = {
                "task":"","can_open_task":0,
                "subject":_("Standalone Tasks Without a Parent Task"),
                "project_workplan":0,"is_group":1,"task_level":"Main Task",
                "assigned_employee":"","assigned_employee_name":"","department":"",
                "branch":"","company":"","project":"","project_name":"","project_status":"",
                "task_type":"","status":"","display_status":"","priority":"","progress":0,
                "exp_start_date":None,"exp_end_date":None,"due_bucket":"",
                "days_remaining":None,"delay_days":0,"expected_days":0,
                "expected_time":0,"actual_time":0,"hours_variance":0,
                "parent_task":"","can_open_parent_task":0,"assigned_by":"",
                "assigned_by_name":"","assignment_type":"","is_milestone":0,
                "completed_on":None,"review_date":None,"closing_date":None,"modified":None,
                "quality_flags":"","quality_issue_count":0,
                "hierarchy_virtual_group":1,
                "hierarchy_number":hierarchy_virtual_root_number,
                "hierarchy_depth":0,
                "hierarchy_root_task":"__STANDALONE_TASKS__",
                "hierarchy_has_children":1,
                "organization_group":"__STANDALONE_TASKS__",
                "organization_group_display":"",
                "group_start":1,
                "group_sequence":hierarchy_root_sequence
            }
            hierarchy_ordered_rows.append(hierarchy_virtual_root)

            hierarchy_standalone_position = 0
            for hierarchy_task_id in hierarchy_standalone_tasks:
                if hierarchy_task_id in hierarchy_visited:
                    continue
                hierarchy_row = hierarchy_row_map.get(hierarchy_task_id)
                if not hierarchy_row:
                    continue
                hierarchy_visited.append(hierarchy_task_id)
                hierarchy_standalone_position = hierarchy_standalone_position + 1
                hierarchy_row["hierarchy_number"] = hierarchy_virtual_root_number + "." + str(hierarchy_standalone_position)
                hierarchy_row["hierarchy_depth"] = 1
                hierarchy_row["hierarchy_root_task"] = "__STANDALONE_TASKS__"
                hierarchy_row["hierarchy_has_children"] = 0
                hierarchy_row["hierarchy_standalone"] = 1
                hierarchy_row["hierarchy_standalone_start"] = 0
                hierarchy_row["organization_group"] = "__STANDALONE_TASKS__"
                hierarchy_row["organization_group_display"] = ""
                hierarchy_row["group_start"] = 0
                hierarchy_row["group_sequence"] = hierarchy_root_sequence
                hierarchy_ordered_rows.append(hierarchy_row)

        # Keep malformed or circular records visible without creating false separators.
        for hierarchy_task_id in hierarchy_task_order:
            if hierarchy_task_id not in hierarchy_visited:
                hierarchy_row = hierarchy_row_map.get(hierarchy_task_id)
                if hierarchy_row:
                    hierarchy_root_sequence = hierarchy_root_sequence + 1
                    hierarchy_row["hierarchy_number"] = str(hierarchy_root_sequence)
                    hierarchy_row["hierarchy_depth"] = 0
                    hierarchy_row["hierarchy_root_task"] = hierarchy_task_id
                    hierarchy_row["hierarchy_has_children"] = 0
                    hierarchy_row["organization_group"] = hierarchy_task_id
                    hierarchy_row["organization_group_display"] = ""
                    hierarchy_row["group_start"] = 1
                    hierarchy_row["group_sequence"] = hierarchy_root_sequence
                    hierarchy_ordered_rows.append(hierarchy_row)

        rows = hierarchy_ordered_rows
    # Pagination is decided only after all database and calculated filters have been
    # applied and the final task order is known.
    total_filtered_records = len(rows)
    if summary_view:
        has_next_page = False
    else:
        has_next_page = total_filtered_records > records_to_load
        if has_next_page:
            rows = rows[:records_to_load]

    for pagination_row in rows:
        pagination_row["_pagination_has_next"] = 1 if has_next_page else 0
        pagination_row["_pagination_page"] = page_number
        pagination_row["_pagination_page_size"] = records_per_page
        pagination_row["_summary_view"] = 1 if summary_view else 0
        pagination_row["_total_filtered_records"] = total_filtered_records

    # Visual group boundaries.
    # Parent Task hierarchy already defines its root boundaries during tree building.
    if organize_by != "Parent Task":
        previous_group = None
        group_sequence = 0
        for r in rows:
            current_group = r.get("organization_group") or ""
            is_new_group = organize_by != "Management Priority" and current_group != previous_group
            if is_new_group:
                group_sequence = group_sequence + 1
            r["group_start"] = 1 if is_new_group else 0
            r["group_sequence"] = group_sequence if organize_by != "Management Priority" else 0
            r["organization_group_display"] = current_group if is_new_group else ""
            previous_group = current_group

    # Operational aggregates.
    regular = []
    for r in rows:
        if int(r.get("project_workplan") or 0) != 1 and int(r.get("hierarchy_virtual_group") or 0) != 1:
            regular.append(r)
    status_counts = {}
    completed = 0
    overdue_count = 0
    pending_review = 0
    due_soon = 0
    urgent = 0
    expected_hours = 0.0
    actual_hours = 0.0
    progress_total = 0.0
    quality_count = 0
    for r in regular:
        st = r.get("display_status") or ""
        status_counts[st] = status_counts.get(st,0) + 1
        if st == "Completed": completed = completed + 1
        if st == "Overdue": overdue_count = overdue_count + 1
        if st == "Pending Review": pending_review = pending_review + 1
        if r.get("due_bucket") in ["Due Today","Due in 3 Days","Due in 7 Days"]: due_soon = due_soon + 1
        if r.get("priority") == "Urgent": urgent = urgent + 1
        expected_hours = expected_hours + float(r.get("expected_time") or 0)
        actual_hours = actual_hours + float(r.get("actual_time") or 0)
        progress_total = progress_total + float(r.get("progress") or 0)
        quality_count = quality_count + int(r.get("quality_issue_count") or 0)
    regular_count = len(regular)
    completion_rate = round(float(completed)*100.0/float(regular_count),1) if regular_count else 0.0
    avg_progress = round(progress_total/float(regular_count),1) if regular_count else 0.0

    # Workload views.
    summary_rows = []
    summary_key = ""
    if view == "Employee Workload": summary_key = "employee"
    elif view == "Department Workload": summary_key = "department"
    elif view == "Project Workload": summary_key = "project"
    if summary_key:
        buckets = {}
        for r in regular:
            key = r.get("assigned_employee_name") if summary_key == "employee" else r.get("department") if summary_key == "department" else r.get("project")
            key = key or "Unassigned"
            if key not in buckets:
                buckets[key] = {"group_name":key,"project":key if summary_key == "project" and key != "Unassigned" else "","project_name":r.get("project_name") if summary_key == "project" else "","total_tasks":0,"open_tasks":0,"working_tasks":0,"pending_review":0,"overdue_tasks":0,"due_soon_tasks":0,"completed_tasks":0,"urgent_tasks":0,"high_tasks":0,"expected_hours":0.0,"actual_hours":0.0,"quality_exceptions":0}
            b = buckets[key]
            b["total_tasks"] = b.get("total_tasks",0) + 1
            st = r.get("display_status")
            pr = r.get("priority")
            if st == "Open": b["open_tasks"] = b.get("open_tasks",0) + 1
            if st == "Working": b["working_tasks"] = b.get("working_tasks",0) + 1
            if st == "Pending Review": b["pending_review"] = b.get("pending_review",0) + 1
            if st == "Overdue": b["overdue_tasks"] = b.get("overdue_tasks",0) + 1
            if r.get("due_bucket") in ["Due Today","Due in 3 Days","Due in 7 Days"]: b["due_soon_tasks"] = b.get("due_soon_tasks",0) + 1
            if st == "Completed": b["completed_tasks"] = b.get("completed_tasks",0) + 1
            if pr == "Urgent": b["urgent_tasks"] = b.get("urgent_tasks",0) + 1
            if pr == "High": b["high_tasks"] = b.get("high_tasks",0) + 1
            b["expected_hours"] = b.get("expected_hours",0) + float(r.get("expected_time") or 0)
            b["actual_hours"] = b.get("actual_hours",0) + float(r.get("actual_time") or 0)
            b["quality_exceptions"] = b.get("quality_exceptions",0) + int(r.get("quality_issue_count") or 0)
        for key in buckets:
            b = buckets.get(key)
            b["hours_variance"] = round(b.get("actual_hours",0)-b.get("expected_hours",0),2)
            b["_pagination_has_next"] = 1 if has_next_page else 0
            b["_pagination_page"] = page_number
            b["_pagination_page_size"] = records_per_page
            b["_summary_view"] = 1
            b["_total_filtered_records"] = total_filtered_records
            summary_rows.append(b)

    # Adaptive columns and sticky identity columns.
    main_column_definitions = [
        {"label":_("Task"),"fieldname":"task","fieldtype":"Data","width":130},
        {"label":_("Task Subject"),"fieldname":"subject","fieldtype":"Data","width":280},
        {"label":_("Workplan"),"fieldname":"project_workplan","fieldtype":"Check","width":75},
        {"label":_("Level"),"fieldname":"task_level","fieldtype":"Data","width":90},
        {"label":_("Employee"),"fieldname":"assigned_employee","fieldtype":"Data","width":135},
        {"label":_("Employee Name"),"fieldname":"assigned_employee_name","fieldtype":"Data","width":175},
        {"label":_("Department"),"fieldname":"department","fieldtype":"Data","width":145},
        {"label":_("Branch"),"fieldname":"branch","fieldtype":"Data","width":125},
        {"label":_("Project Code"),"fieldname":"project","fieldtype":"Data","width":140},
        {"label":_("Project Name"),"fieldname":"project_name","fieldtype":"Data","width":230},
        {"label":_("Task Type"),"fieldname":"task_type","fieldtype":"Data","width":115},
        {"label":_("Status"),"fieldname":"display_status","fieldtype":"Data","width":115},
        {"label":_("Priority"),"fieldname":"priority","fieldtype":"Data","width":90},
        {"label":_("Progress"),"fieldname":"progress","fieldtype":"Percent","width":105},
        {"label":_("Due Bucket"),"fieldname":"due_bucket","fieldtype":"Data","width":110},
        {"label":_("Start"),"fieldname":"exp_start_date","fieldtype":"Datetime","width":145},
        {"label":_("Due"),"fieldname":"exp_end_date","fieldtype":"Datetime","width":145},
        {"label":_("Days Remaining"),"fieldname":"days_remaining","fieldtype":"Int","width":110},
        {"label":_("Delay Days"),"fieldname":"delay_days","fieldtype":"Int","width":90},
        {"label":_("Expected Hours"),"fieldname":"expected_time","fieldtype":"Float","precision":2,"width":105},
        {"label":_("Actual Hours"),"fieldname":"actual_time","fieldtype":"Float","precision":2,"width":100},
        {"label":_("Hours Variance"),"fieldname":"hours_variance","fieldtype":"Float","precision":2,"width":105},
        {"label":_("Parent Task"),"fieldname":"parent_task","fieldtype":"Data","width":130},
        {"label":_("Assigned By"),"fieldname":"assigned_by","fieldtype":"Data","width":130},
        {"label":_("Assignment Type"),"fieldname":"assignment_type","fieldtype":"Data","width":110},
        {"label":_("Milestone"),"fieldname":"is_milestone","fieldtype":"Check","width":80},
        {"label":_("Quality Flags"),"fieldname":"quality_flags","fieldtype":"Data","width":255}
    ]

    pinned_main_fields = ["task","subject"]
    if organize_by == "Project":
        pinned_main_fields = ["project","project_name"]
    elif organize_by == "Employee":
        pinned_main_fields = ["assigned_employee","assigned_employee_name"]
    elif organize_by == "Department":
        pinned_main_fields = ["department","assigned_employee_name"]
    elif organize_by == "Branch":
        pinned_main_fields = ["branch","assigned_employee_name"]
    elif organize_by == "Task Type":
        pinned_main_fields = ["task_type","subject"]
    elif organize_by == "Status":
        pinned_main_fields = ["display_status","subject"]
    elif organize_by == "Priority":
        pinned_main_fields = ["priority","subject"]

    main_cols = []
    for pinned_fieldname in pinned_main_fields:
        for column_definition in main_column_definitions:
            if column_definition.get("fieldname") == pinned_fieldname:
                pinned_column = {}
                for column_key in column_definition:
                    pinned_column[column_key] = column_definition.get(column_key)
                pinned_column["sticky"] = 1
                main_cols.append(pinned_column)
                break

    if show_group_column and organize_by not in ["Management Priority","Parent Task"]:
        main_cols.append({"label":_("Organized By"),"fieldname":"organization_group_display","fieldtype":"Data","width":190})

    for column_definition in main_column_definitions:
        if column_definition.get("fieldname") not in pinned_main_fields:
            main_cols.append(column_definition)

    summary_cols = [
        {"label":_("Group"),"fieldname":"group_name","fieldtype":"Data","width":210,"sticky":1},
        {"label":_("Total"),"fieldname":"total_tasks","fieldtype":"Int","width":70,"sticky":1},
        {"label":_("Open"),"fieldname":"open_tasks","fieldtype":"Int","width":70},
        {"label":_("Working"),"fieldname":"working_tasks","fieldtype":"Int","width":75},
        {"label":_("Pending Review"),"fieldname":"pending_review","fieldtype":"Int","width":105},
        {"label":_("Overdue"),"fieldname":"overdue_tasks","fieldtype":"Int","width":75},
        {"label":_("Due Soon"),"fieldname":"due_soon_tasks","fieldtype":"Int","width":80},
        {"label":_("Completed"),"fieldname":"completed_tasks","fieldtype":"Int","width":85},
        {"label":_("Urgent"),"fieldname":"urgent_tasks","fieldtype":"Int","width":70},
        {"label":_("High"),"fieldname":"high_tasks","fieldtype":"Int","width":65},
        {"label":_("Expected Hours"),"fieldname":"expected_hours","fieldtype":"Float","precision":2,"width":110},
        {"label":_("Actual Hours"),"fieldname":"actual_hours","fieldtype":"Float","precision":2,"width":105},
        {"label":_("Hours Variance"),"fieldname":"hours_variance","fieldtype":"Float","precision":2,"width":105},
        {"label":_("Quality Exceptions"),"fieldname":"quality_exceptions","fieldtype":"Int","width":115}
    ]
    project_summary_cols = [
        {"label":_("Project Code"),"fieldname":"project","fieldtype":"Data","width":145,"sticky":1},
        {"label":_("Project Name"),"fieldname":"project_name","fieldtype":"Data","width":260,"sticky":1}
    ]
    for col in summary_cols:
        if col.get("fieldname") not in ["group_name","total_tasks"]:
            project_summary_cols.append(col)
    if summary_key:
        data_rows = summary_rows
        columns = project_summary_cols if summary_key == "project" else summary_cols
    else:
        data_rows = rows
        columns = main_cols

    report_summary = [{"value":len(rows),"indicator":"Blue","label":_("Visible Records"),"datatype":"Int"},{"value":regular_count,"indicator":"Blue","label":_("Regular Tasks"),"datatype":"Int"},{"value":len(rows)-regular_count,"indicator":"Blue","label":_("Project Workplans"),"datatype":"Int"},{"value":completed,"indicator":"Green","label":_("Completed"),"datatype":"Int"},{"value":overdue_count,"indicator":"Red","label":_("Overdue"),"datatype":"Int"},{"value":due_soon,"indicator":"Orange","label":_("Due Soon"),"datatype":"Int"},{"value":pending_review,"indicator":"Orange","label":_("Pending Review"),"datatype":"Int"},{"value":urgent,"indicator":"Red","label":_("Urgent"),"datatype":"Int"},{"value":completion_rate,"indicator":"Green" if completion_rate >= 75 else "Orange" if completion_rate >= 50 else "Red","label":_("Completion Rate"),"datatype":"Percent"},{"value":avg_progress,"indicator":"Blue","label":_("Average Progress"),"datatype":"Percent"},{"value":round(expected_hours,2),"indicator":"Blue","label":_("Expected Hours"),"datatype":"Float"},{"value":round(actual_hours,2),"indicator":"Orange","label":_("Actual Hours"),"datatype":"Float"},{"value":quality_count,"indicator":"Red" if quality_count else "Green","label":_("Data Exceptions"),"datatype":"Int"}]
    chart = {"data":{"labels":[_("Open"),_("Working"),_("Pending Review"),_("Overdue"),_("Due Soon"),_("Completed")],"datasets":[{"name":_("Regular Tasks"),"values":[status_counts.get("Open",0),status_counts.get("Working",0),status_counts.get("Pending Review",0),status_counts.get("Overdue",0),due_soon,status_counts.get("Completed",0)]}]},"type":"bar","height":280,"colors":["#2490EF"]}
    displayed_records = len(rows)
    scope_text = _("My assigned tasks") if my_tasks_only else _("All matching tasks")
    year_text = selected_year if selected_year else _("All Years")
    if summary_view:
        message = _("{0}: the workload summary is calculated from all {1} Task records matching the active filters for {2}. Record loading limits do not affect this summary, its indicators, or its chart.").replace("{0}",scope_text).replace("{1}",str(total_filtered_records)).replace("{2}",year_text)
    else:
        more_text = _("Use Load More to display the next group of records.") if has_next_page else _("All matching records are currently displayed.")
        message = _("{0}: displaying {1} of {2} matching records for {3}. Each Load More click adds up to {4} records. {5} Summary cards and the chart represent all records currently displayed.").replace("{0}",scope_text).replace("{1}",str(displayed_records)).replace("{2}",str(total_filtered_records)).replace("{3}",year_text).replace("{4}",str(records_per_page)).replace("{5}",more_text)
    if my_tasks_only and not current_employee:
        message = _("My Tasks Only is enabled, but no active Employee is linked to the current user through custom_user_id or user_id.")
    data = (columns,data_rows,message,chart,report_summary,0)
    return data
