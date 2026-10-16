from __future__ import annotations

from datetime import timedelta
import json

import frappe
from frappe import _
from frappe.utils import add_days, add_months, flt, get_datetime, get_first_day, get_last_day, getdate, now, now_datetime, today

from qfap_adds.qfap_adds.task_management.settings import get_additional_recipient_emails, get_settings

WEEKDAYS = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}


def _period(settings, reference_date=None):
    ref = getdate(reference_date or today())
    mode = settings.summary_period_mode or "Automatic by Frequency"
    if mode == "Automatic by Frequency":
        mode = {"Daily":"Current Day", "Weekly":"Current Week", "Monthly":"Current Month"}.get(settings.summary_frequency, "Current Week")
    if mode == "Current Day": start = end = ref
    elif mode == "Previous Day": start = end = getdate(add_days(ref, -1))
    elif mode in ("Current Week", "Previous Week"):
        shift = -7 if mode == "Previous Week" else 0
        anchor = getdate(add_days(ref, shift)); start = getdate(add_days(anchor, -anchor.weekday())); end = getdate(add_days(start, 6))
    elif mode in ("Current Month", "Previous Month"):
        anchor = getdate(add_months(ref, -1)) if mode == "Previous Month" else ref
        start = getdate(get_first_day(anchor)); end = getdate(get_last_day(anchor))
    else:
        days = max(1, int(settings.summary_rolling_days or 7)); end = ref; start = getdate(add_days(end, -(days - 1)))
    return {"start": start, "end": end, "label": f"{frappe.format(start, {'fieldtype':'Date'})} - {frappe.format(end, {'fieldtype':'Date'})}"}


def _filter_sets(settings):
    result = {"Status": set(), "Priority": set(), "Task Type": set(), "Project": set()}
    for row in settings.get("summary_filter_rows") or []:
        if not int(row.get("enabled") or 0): continue
        value = row.get(frappe.scrub(row.filter_type))
        if value: result[row.filter_type].add(value)
    return result


def _task_rows(employee, settings, period, reference_date=None):
    ref = getdate(reference_date or period["end"])
    filters = _filter_sets(settings)
    rows = frappe.get_all(
        "Task", filters={"custom_assign_to": employee, "is_template": 0},
        fields=["name","subject","project","type","status","priority","progress","exp_start_date","exp_end_date","expected_time","actual_time","parent_task","is_group","custom_project_workplan","custom_task_assigned_by","modified","completed_on"],
        order_by="exp_end_date asc, priority desc, modified desc", limit_page_length=10000,
    )
    output=[]
    for row in rows:
        if row.status in ("Cancelled","Template"): continue
        is_main=bool(row.is_group); is_workplan=bool(row.custom_project_workplan)
        if is_workplan and not int(settings.summary_include_workplan or 0): continue
        if is_main and not int(settings.summary_include_main_tasks or 0): continue
        if not is_main and not is_workplan and not int(settings.summary_include_operational or 0): continue
        if filters["Status"] and row.status not in filters["Status"]: continue
        if filters["Priority"] and row.priority not in filters["Priority"]: continue
        if filters["Task Type"] and row.type not in filters["Task Type"]: continue
        if filters["Project"] and row.project not in filters["Project"]: continue
        if int(settings.summary_exclude_zero_hours or 0) and flt(row.expected_time)<=0: continue
        start=getdate(row.exp_start_date) if row.exp_start_date else None; end=getdate(row.exp_end_date) if row.exp_end_date else None
        completed_date=getdate(row.completed_on) if row.completed_on else None
        overdue=bool(row.status!='Completed' and end and end<ref)
        due_soon=bool(row.status!='Completed' and end and ref<=end<=getdate(add_days(ref,int(settings.summary_due_soon_days or 7))))
        stale=bool(getdate(row.modified)<=getdate(add_days(ref,-int(settings.summary_stale_days or 7))))
        low_progress=bool(row.status!='Completed' and flt(row.progress)<flt(settings.summary_progress_warning or 25))
        zero_hours=flt(row.expected_time)<=0
        in_period=bool((start and end and start<=period['end'] and end>=period['start']) or (completed_date and period['start']<=completed_date<=period['end']))
        carried=bool(row.status!='Completed' and end and end<period['start'])
        undated=not start and not end
        include=in_period or (carried and int(settings.summary_include_carried_forward or 0)) or (undated and int(settings.summary_include_undated or 0))
        if overdue and int(settings.summary_include_overdue or 0): include=True
        if due_soon and int(settings.summary_include_due_soon or 0): include=True
        if row.status=='Completed' and not int(settings.summary_include_completed or 0): include=False
        attention=overdue or due_soon or stale or low_progress or zero_hours
        if int(settings.summary_only_attention or 0) and not attention: include=False
        if not include: continue
        row.update({"is_main":is_main,"is_workplan":is_workplan,"overdue":overdue,"due_soon":due_soon,"stale":stale,"low_progress":low_progress,"zero_hours":zero_hours,"attention":attention,"task_url":frappe.utils.get_url_to_form("Task",row.name)})
        output.append(row)
    return output


def _columns(settings):
    result=[("subject","Subject")]
    for enabled,key,label in [
        (settings.summary_show_project,"project","Project"),(settings.summary_show_task_type,"type","Task Type"),(settings.summary_show_status,"status","Status"),(settings.summary_show_priority,"priority","Priority"),(settings.summary_show_progress,"progress","Progress"),(settings.summary_show_due_date,"exp_end_date","Due Date"),(settings.summary_show_expected_hours,"expected_time","Expected Hours"),(settings.summary_show_actual_hours,"actual_time","Actual Hours"),(settings.summary_show_assigned_by,"custom_task_assigned_by","Assigned By")]:
        if int(enabled or 0): result.append((key,label))
    return result


def _fallback_html(context):
    cards=[("Operational",context['operational_task_count']), ("Main Tasks",context['main_task_count']), ("Overdue",context['overdue_count']), ("Due Soon",context['due_soon_count']), ("Average Progress",str(context['average_progress'])+'%'), ("Expected Hours",context['expected_hours']), ("Actual Hours",context['actual_hours'])]
    card_html=''.join(f'<td style="padding:10px;border:1px solid #dbe4ea;background:#f8fafc;text-align:center"><b>{frappe.utils.escape_html(str(v))}</b><br><span style="font-size:11px;color:#64748b">{frappe.utils.escape_html(k)}</span></td>' for k,v in cards)
    return f'<div style="font-family:Arial,sans-serif;color:#1f2937"><h2 style="color:#155f78">Task Summary</h2><p><b>{frappe.utils.escape_html(context["employee_name"])}</b><br>{frappe.utils.escape_html(context["period_label"])}</p><table style="width:100%;border-collapse:collapse"><tr>{card_html}</tr></table><p style="margin-top:20px"><a href="{context["report_url"]}">Open Employees Task Tracker</a></p></div>'


def build_summary_context(employee, reference_date=None, settings=None):
    settings=settings or get_settings(); period=_period(settings,reference_date)
    info=frappe.db.get_value("Employee",employee,["employee_name","department","designation","company","user_id"],as_dict=True) or {}
    tasks=_task_rows(employee,settings,period,reference_date)
    operational=[x for x in tasks if not x.is_main and not x.is_workplan]; main=[x for x in tasks if x.is_main]; attention=[x for x in tasks if x.attention]
    max_rows=max(1,int(settings.summary_max_tasks or 25)); level=settings.summary_detail_level or "Full Task Details"
    visible=[] if level=="Summary Only" else (attention if level=="Summary and Attention Tasks" else tasks)
    context={"employee":info,"employee_id":employee,"employee_name":info.get('employee_name') or employee,"department":info.get('department') or '',"designation":info.get('designation') or '',"company":info.get('company') or '',"frequency":settings.summary_frequency or 'Weekly',"report_date":frappe.format(getdate(reference_date or today()),{'fieldtype':'Date'}),"period_start":period['start'],"period_end":period['end'],"period_label":period['label'],"report_url":frappe.utils.get_url()+"/app/query-report/Employees%20Task%20Tracker?my_tasks_only=1","operational_tasks":operational[:max_rows],"main_tasks":main[:max_rows],"attention_tasks":attention[:max_rows],"overdue_tasks":[x for x in tasks if x.overdue][:max_rows],"due_soon_tasks":[x for x in tasks if x.due_soon][:max_rows],"display_tasks":visible[:max_rows],"columns":_columns(settings),"operational_task_count":len(operational),"main_task_count":len(main),"total_tasks":len(tasks),"active_tasks":sum(1 for x in tasks if x.status!='Completed'),"completed_tasks":sum(1 for x in tasks if x.status=='Completed'),"overdue_count":sum(1 for x in tasks if x.overdue),"due_soon_count":sum(1 for x in tasks if x.due_soon),"average_progress":round(sum(flt(x.progress) for x in operational)/len(operational),2) if operational else 0,"expected_hours":round(sum(flt(x.expected_time) for x in operational),2),"actual_hours":round(sum(flt(x.actual_time) for x in operational),2),"detail_level":level}
    context['generated_summary_html']=_fallback_html(context)
    return context


def render_employee_summary(employee, reference_date=None, settings=None):
    settings=settings or get_settings(); context=build_summary_context(employee,reference_date,settings)
    subject=(settings.summary_email_subject or "Task Summary | {employee_name} | {report_date}").format(employee_name=context['employee_name'],report_date=context['report_date'],frequency=context['frequency'])
    message=context['generated_summary_html']; template_name=settings.summary_email_template
    if template_name and frappe.db.exists("Email Template",template_name):
        template=frappe.get_doc("Email Template",template_name)
        subject=frappe.render_template(template.subject or subject,context)
        body=template.response_html or template.response
        if body: message=frappe.render_template(body,context)
    return {"subject":subject,"message":message,"context":context}


def _employee_rows():
    return frappe.db.sql('''SELECT e.name employee,e.user_id,u.email FROM `tabEmployee` e INNER JOIN `tabUser` u ON u.name=e.user_id WHERE e.status='Active' AND IFNULL(u.enabled,0)=1 AND IFNULL(u.email,'')!='' ORDER BY e.employee_name''',as_dict=True)


def send_employee_task_summary(force=False, reference_date=None, only_employee=None, test_recipient=None):
    settings=get_settings()
    if not force and not int(settings.summary_schedule_enabled or 0): return {"sent":0,"skipped":True}
    additional=[] if test_recipient else get_additional_recipient_emails(settings); sent=0; skipped=0
    rows=_employee_rows()
    if only_employee: rows=[r for r in rows if r.employee==only_employee]
    for row in rows:
        rendered=render_employee_summary(row.employee,reference_date,settings)
        recipients=[test_recipient] if test_recipient else list(dict.fromkeys(([row.email] if int(settings.summary_send_to_employees or 0) else [])+additional))
        if not recipients: skipped+=1; continue
        frappe.sendmail(recipients=recipients,subject=rendered['subject'],message=rendered['message'],reference_doctype='Employee',reference_name=row.employee,delayed=True)
        sent+=1
    return {"sent":sent,"skipped":skipped,"additional_recipients":len(additional)}


@frappe.whitelist()
def preview_task_summary(employee, reference_date=None):
    _require_admin(); return render_employee_summary(employee,reference_date)["message"]


@frappe.whitelist()
def send_test_summary(employee, recipient, reference_date=None):
    _require_admin()
    from frappe.utils import validate_email_address
    if not validate_email_address(recipient,throw=False): frappe.throw(_("Enter a valid test email address."))
    return send_employee_task_summary(True,reference_date,employee,recipient)


def _require_admin():
    settings=get_settings()
    if frappe.session.user!='Administrator' and settings.administrative_role not in frappe.get_roles(): frappe.throw(_("Only Task Management Administrators can perform this action."))


def _period_key(settings,current):
    if settings.summary_frequency=='Daily': return current.strftime('D:%Y-%m-%d')
    if settings.summary_frequency=='Monthly': return current.strftime('M:%Y-%m')
    year,week,_=current.isocalendar(); return f'W:{year}-{week:02d}'


def _is_due(settings,current):
    if not int(settings.summary_schedule_enabled or 0): return False
    if current.strftime('%H:%M')<str(settings.summary_send_time or '08:00:00')[:5]: return False
    if settings.summary_frequency=='Weekly' and current.weekday()!=WEEKDAYS.get(settings.summary_weekly_day,6): return False
    if settings.summary_frequency=='Monthly' and current.day!=int(settings.summary_monthly_day or 1): return False
    return True


def get_next_send_datetime(settings=None,current=None):
    settings=settings or get_settings(); current=current or get_datetime(now()); parts=str(settings.summary_send_time or '08:00:00').split(':'); candidate=current.replace(hour=int(parts[0]),minute=int(parts[1]),second=0,microsecond=0)
    if settings.summary_frequency=='Daily': return candidate+timedelta(days=1) if candidate<=current else candidate
    if settings.summary_frequency=='Weekly':
        candidate+=timedelta(days=(WEEKDAYS.get(settings.summary_weekly_day,6)-candidate.weekday())%7); return candidate+timedelta(days=7) if candidate<=current else candidate
    day=max(1,min(28,int(settings.summary_monthly_day or 1))); candidate=candidate.replace(day=day)
    if candidate<=current:
        year=candidate.year+(1 if candidate.month==12 else 0); month=1 if candidate.month==12 else candidate.month+1; candidate=candidate.replace(year=year,month=month,day=day)
    return candidate


def run_scheduled_task_summary():
    settings=get_settings(); current=get_datetime(now()); key=_period_key(settings,current)
    if not _is_due(settings,current) or settings.summary_last_period_key==key: return {"sent":0,"due":False,"period_key":key}
    return _run_and_record(key,False)


@frappe.whitelist()
def send_task_summary_now(): _require_admin(); return _run_and_record('MANUAL:'+now_datetime().strftime('%Y%m%d%H%M%S'),True)


def _run_and_record(key,manual=False):
    try:
        result=send_employee_task_summary(True); values={"summary_last_sent_on":now(),"summary_last_send_status":"Completed","summary_last_send_summary":frappe.as_json(result),"summary_next_send_on":get_next_send_datetime()}
        if not manual: values['summary_last_period_key']=key
        for field,value in values.items(): frappe.db.set_single_value('Task Management Settings',field,value)
        frappe.db.commit(); return result
    except Exception:
        error=frappe.get_traceback(); frappe.db.set_single_value('Task Management Settings','summary_last_send_status','Failed'); frappe.db.set_single_value('Task Management Settings','summary_last_send_summary',error); frappe.log_error(error,'Scheduled Task Summary'); raise


def weekly_employee_task_summary(): return run_scheduled_task_summary()
