from qfap_adds.qfap_adds.project_management.reporting import generic

def execute(filters=None):
    return generic('Project Indicator', filters, ['indicator_code', 'indicator_name', 'life_of_project_target'])
