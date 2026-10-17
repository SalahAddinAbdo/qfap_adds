from qfap_adds.qfap_adds.project_management.reporting import generic

def execute(filters=None):
    return generic('Project Change Request', filters, ['change_title', 'change_type', 'overall_impact_level', 'implementation_status'])
