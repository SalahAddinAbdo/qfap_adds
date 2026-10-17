from qfap_adds.qfap_adds.project_management.reporting import generic

def execute(filters=None):
    return generic('Project Compliance Deliverable', filters, ['deliverable_name', 'due_date', 'monitoring_status', 'responsible_employee'])
