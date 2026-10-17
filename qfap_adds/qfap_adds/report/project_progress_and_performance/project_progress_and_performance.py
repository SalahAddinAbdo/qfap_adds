from qfap_adds.qfap_adds.project_management.reporting import generic

def execute(filters=None):
    return generic('Project Progress Update', filters, ['period_start_date', 'period_end_date', 'overall_progress'])
