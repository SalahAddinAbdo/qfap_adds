from qfap_adds.qfap_adds.project_management.reporting import generic

def execute(filters=None):
    return generic('Project Risk', filters, ['risk_title', 'risk_level', 'risk_score', 'risk_owner', 'next_review_date'])
