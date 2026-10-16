from qfap_adds.qfap_adds.task_management.settings import get_settings

def get_task_settings(): return get_settings()
def role_lines(value): return [x.strip() for x in str(value or "").replace(",","\n").splitlines() if x.strip()]
