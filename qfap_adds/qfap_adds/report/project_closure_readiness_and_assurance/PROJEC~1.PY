from qfap_adds.qfap_adds.project_management.reporting import generic

def execute(filters=None):
    return generic('Project Closure', filters, ['overall_closure_status', 'planned_closure_date', 'actual_closure_date', 'project_closed'])
