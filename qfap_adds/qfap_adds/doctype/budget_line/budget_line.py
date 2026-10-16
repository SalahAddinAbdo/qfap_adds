from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import NestedSet


class BudgetLine(NestedSet):
    nsm_parent_field = "parent_budget_line"

    def before_insert(self):
        self._validate_project()
        self._set_new_code_and_sequence()

    def validate(self):
        self._validate_project()
        self._validate_parent()
        self._validate_single_root()
        self._validate_status_and_amount()
        self._protect_locked_values()
        self._set_lock_state()

    def on_update(self):
        self._rollup_project_groups()
        frappe.db.set_value(self.doctype, self.name, "old_parent", self.parent_budget_line or "", update_modified=False)

    def on_trash(self):
        if self.is_group and frappe.db.exists(self.doctype, {"parent_budget_line": self.name}):
            frappe.throw(_("A group Budget Line cannot be deleted while it has child Budget Lines."))

    def after_delete(self):
        self._rollup_project_groups()

    def _validate_project(self):
        if not self.project:
            frappe.throw(_("Project is required."))

    def _validate_single_root(self):
        if self.is_group and not self.parent_budget_line:
            filters = {"project": self.project, "is_group": 1, "parent_budget_line": ["is", "not set"]}
            if self.name:
                filters["name"] = ["!=", self.name]
            if frappe.db.exists(self.doctype, filters):
                frappe.throw(_("Only one root Budget Line is allowed for each Project."))
        elif not self.parent_budget_line:
            frappe.throw(_("Every Budget Line except the Project root must have a Parent Budget Line."))

    def _validate_parent(self):
        if not self.parent_budget_line:
            return
        parent = frappe.db.get_value(self.doctype, self.parent_budget_line,
            ["project", "is_group", "status", "parent_budget_line", "budget_line", "currency"], as_dict=True)
        if not parent:
            frappe.throw(_("Parent Budget Line was not found."))
        if parent.project != self.project:
            frappe.throw(_("Parent Budget Line must belong to the selected Project."))
        if not parent.is_group:
            frappe.throw(_("Parent Budget Line must be a group."))
        if parent.status == "Inactive":
            frappe.throw(_("Inactive Budget Lines cannot be selected as parents."))
        if parent.currency and self.currency and parent.currency != self.currency:
            frappe.throw(_("Budget Line currency must match the parent currency."))

    def _set_new_code_and_sequence(self):
        is_root = self.is_group and not self.parent_budget_line
        if is_root:
            self.sequence = 0; self.use_custom_code = 0; self.budget_line = self.project
            return
        if not self.parent_budget_line:
            return
        parent = frappe.db.get_value(self.doctype, self.parent_budget_line,
            ["parent_budget_line", "budget_line", "currency"], as_dict=True)
        siblings = frappe.get_all(self.doctype, filters={"project": self.project, "parent_budget_line": self.parent_budget_line},
            pluck="sequence", order_by="sequence desc", limit=1)
        self.sequence = int((siblings[0] if siblings else 0) or 0) + 1
        if not self.currency and parent:
            self.currency = parent.currency
        if not self.use_custom_code and parent:
            if not parent.parent_budget_line:
                letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                if self.sequence > len(letters):
                    frappe.throw(_("Automatic top-level coding supports up to 26 Budget Lines."))
                self.budget_line = f"{parent.budget_line}-{letters[self.sequence - 1]}"
            else:
                self.budget_line = f"{parent.budget_line}.{self.sequence}"

    def _validate_status_and_amount(self):
        if self.status == "Inactive" and self.is_group and frappe.db.exists(self.doctype,
            {"parent_budget_line": self.name, "status": ["!=", "Inactive"]}):
            frappe.throw(_("A group with active child Budget Lines cannot be made Inactive."))
        if flt(self.line_cost) < 0:
            frappe.throw(_("Approved Budget Amount cannot be negative."))
        old_status = self.get_db_value("status") if not self.is_new() else None
        if self.status == "Approved" and old_status != "Approved" and not self.is_group:
            self.original_approved_amount = flt(self.line_cost)

    def _protect_locked_values(self):
        if self.is_new() or not self.get_db_value("budget_line_locked"):
            return
        old = frappe.db.get_value(self.doctype, self.name,
            ["project", "parent_budget_line", "budget_line", "currency", "line_cost", "name1", "status"], as_dict=True)
        if not old:
            return
        changed = [f for f in old if str(old.get(f) or "") != str(self.get(f) or "")]
        if changed and not self._has_active_change_request():
            frappe.throw(_("This approved Budget Line is locked. Use an active Project Change Request."))

    def _has_active_change_request(self):
        if not self.latest_change_request or not frappe.db.exists("DocType", "Project Change Request"):
            return False
        request = frappe.db.get_value("Project Change Request", self.latest_change_request,
            ["docstatus", "implementation_status"], as_dict=True)
        if not request or request.docstatus != 1 or request.implementation_status != "In Progress":
            return False
        if not frappe.db.exists("DocType", "Project Change Affected Item"):
            return False
        return bool(frappe.db.exists("Project Change Affected Item", {
            "parent": self.latest_change_request, "parenttype": "Project Change Request",
            "reference_doctype": self.doctype, "reference_document": self.name,
            "implementation_status": ["in", ["Not Started", "In Progress"]]}))

    def _set_lock_state(self):
        if self.status in ("Approved", "Inactive"):
            self.budget_line_locked = 0 if self._has_active_change_request() else 1
        else:
            self.budget_line_locked = 0

    def _rollup_project_groups(self):
        if not self.project:
            return
        groups = frappe.get_all(self.doctype, filters={"project": self.project, "is_group": 1},
            fields=["name", "lft"], order_by="lft desc", limit_page_length=0)
        for group in groups:
            children = frappe.get_all(self.doctype,
                filters={"parent_budget_line": group.name, "status": "Approved"}, pluck="line_cost", limit_page_length=0)
            frappe.db.set_value(self.doctype, group.name, "line_cost", sum(flt(v) for v in children), update_modified=False)


@frappe.whitelist()
def get_tree_nodes(doctype=None, parent=None, filters=None, project=None, is_root=False, **kwargs):
    """Return the real per-Project Budget Line hierarchy.

    Frappe may send the selected Project in ``filters`` as a dict, a list, or a
    JSON string. When a Project filter is active, Frappe may also send the
    Project name itself as ``parent`` while expanding the visible Project root.
    This method normalizes both cases and maps that visible Project root to the
    actual root Budget Line document before fetching children.
    """
    parsed_filters = filters
    if isinstance(parsed_filters, str):
        try:
            parsed_filters = frappe.parse_json(parsed_filters)
        except Exception:
            parsed_filters = {}

    selected_project = project or ""
    if isinstance(parsed_filters, dict):
        selected_project = selected_project or parsed_filters.get("project") or ""
    elif isinstance(parsed_filters, (list, tuple)):
        for item in parsed_filters:
            if isinstance(item, dict) and item.get("fieldname") == "project":
                selected_project = selected_project or item.get("value") or ""
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                # Supports [field, value], [field, operator, value], and
                # [doctype, field, operator, value] filter formats.
                if item[0] == "project":
                    selected_project = selected_project or item[-1] or ""
                elif len(item) >= 4 and item[1] == "project":
                    selected_project = selected_project or item[-1] or ""

    current_parent = (parent or "").strip()
    root_labels = {"", "Budget Line", "Budget Lines", _("Budget Lines")}
    root_request = bool(frappe.utils.cint(is_root) or current_parent in root_labels)

    # With a selected Project, the visible first node can use the Project name
    # as its value. Resolve it to the actual root Budget Line document.
    if not root_request:
        parent_is_budget_line = frappe.db.exists("Budget Line", current_parent)
        parent_is_project = frappe.db.exists("Project", current_parent)
        if not parent_is_budget_line and (parent_is_project or current_parent == selected_project):
            project_for_root = selected_project or current_parent
            actual_root = frappe.db.get_value(
                "Budget Line",
                {
                    "project": project_for_root,
                    "parent_budget_line": ["is", "not set"],
                    "is_group": 1,
                },
                "name",
            )
            if not actual_root:
                return []
            current_parent = actual_root
            selected_project = project_for_root

    node_filters = {}
    if selected_project:
        node_filters["project"] = selected_project

    if root_request:
        node_filters["parent_budget_line"] = ["is", "not set"]
        node_filters["is_group"] = 1
    else:
        node_filters["parent_budget_line"] = current_parent

    rows = frappe.get_list(
        "Budget Line",
        filters=node_filters,
        fields=[
            "name",
            "name1",
            "budget_line",
            "project",
            "parent_budget_line",
            "is_group",
            "lft",
            "rgt",
        ],
        order_by="project asc, lft asc",
        limit_page_length=0,
    )

    nodes = []
    for row in rows:
        is_project_root = not row.parent_budget_line
        nodes.append(
            {
                "value": row.name,
                "title": row.project if is_project_root else (row.name1 or row.budget_line or row.name),
                "expandable": 1 if frappe.utils.cint(row.is_group) else 0,
                "project": row.project,
                "is_project_root": 1 if is_project_root else 0,
            }
        )
    return nodes
