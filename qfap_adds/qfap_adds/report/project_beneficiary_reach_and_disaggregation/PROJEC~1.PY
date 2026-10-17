from qfap_adds.qfap_adds.project_management.reporting import generic

def execute(filters=None):
    return generic('Project Beneficiary Plan', filters, ['planned_individuals_total', 'actual_individuals_total', 'individual_achievement_total'])
