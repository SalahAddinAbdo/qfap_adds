from __future__ import annotations
from qfap_adds.qfap_adds.project_management.report_link_titles import finalize_report_result
import re
import frappe
from frappe import _
from frappe.utils import flt, nowdate

def _sort_key(name):
    match=re.search(r"-BL\.([0-9.]+)",str(name or ""))
    if not match:return (0,(),str(name or ""))
    return (1,tuple(int(x) for x in match.group(1).split(".") if x.isdigit()),str(name or ""))

def execute(filters=None):
    filters=frappe._dict(filters or {})
    company=filters.get("company"); project=filters.get("project")
    from_date=filters.get("from_date") or "1900-01-01"; to_date=filters.get("to_date") or nowdate()
    if not company:return [],[],_("Select a Company."),None,[]
    if from_date>to_date:frappe.throw(_("From Date cannot be later than To Date."))
    currency=frappe.db.get_value("Company",company,"default_currency")
    columns=[
      {"label":_("Budget Line"),"fieldname":"budget_line","fieldtype":"Link","options":"Budget Line","width":330,"sticky":True},
      {"label":_("Account"),"fieldname":"account","fieldtype":"Link","options":"Account","width":270,"sticky":True},
      {"label":_("Budget Amount"),"fieldname":"budget_amount","fieldtype":"Currency","options":"currency","width":135},
      {"label":_("Actual Expense"),"fieldname":"actual_amount","fieldtype":"Currency","options":"currency","width":135},
      {"label":_("Available Balance"),"fieldname":"variance","fieldtype":"Currency","options":"currency","width":140},
      {"label":_("Utilization %"),"fieldname":"utilization_percentage","fieldtype":"Percent","width":110},
      {"label":_("Performance Status"),"fieldname":"performance_status","fieldtype":"Data","width":155},
    ]
    lines=frappe.get_all("Budget Line",fields=["name","parent_budget_line","is_group","project","line_cost","lft"],order_by="lft asc",limit_page_length=0)
    by_name={x.name:x for x in lines};children={}
    for x in lines:children.setdefault(x.parent_budget_line,[]).append(x.name)
    for values in children.values():values.sort(key=_sort_key)
    included=set()
    if project:
      for x in lines:
       if x.project==project:
        cur=x.name;seen=set()
        while cur and cur not in seen:
         seen.add(cur);included.add(cur);cur=by_name.get(cur).parent_budget_line if by_name.get(cur) else None
    else:included={x.name for x in lines}
    roots=sorted([x for x in included if not by_name[x].parent_budget_line or by_name[x].parent_budget_line not in included],key=_sort_key)
    ordered=[];stack=list(reversed(roots))
    while stack:
      name=stack.pop()
      if name in ordered:continue
      ordered.append(name)
      stack.extend(reversed([x for x in children.get(name,[]) if x in included]))
    if not ordered:return columns,[],_("No Budget Lines match the selected filters."),None,[]
    args={"company":company,"from_date":from_date,"to_date":to_date,"budget_lines":tuple(ordered)}
    account_clause="AND acc.root_type='Expense'"
    selected_assets=filters.get("asset_accounts") or []
    if isinstance(selected_assets,str):selected_assets=[selected_assets]
    if int(filters.get("include_asset_expenses") or 0) and selected_assets:
      asset_rows=frappe.db.sql("""select leaf.name from `tabAccount` root join `tabAccount` leaf on leaf.lft>=root.lft and leaf.rgt<=root.rgt where root.name in %(roots)s and root.company=%(company)s and leaf.is_group=0 and leaf.disabled=0 and leaf.root_type='Asset'""",{"roots":tuple(selected_assets),"company":company},as_dict=True)
      asset_names=tuple(x.name for x in asset_rows)
      if asset_names:args["assets"]=asset_names;account_clause="AND (acc.root_type='Expense' OR gle.account IN %(assets)s)"
    actuals=frappe.db.sql("""select gle.budget_line,gle.account,acc.root_type,sum(gle.debit-gle.credit) actual_amount from `tabGL Entry` gle join `tabAccount` acc on acc.name=gle.account where gle.docstatus=1 and gle.is_cancelled=0 and gle.company=%(company)s and gle.posting_date between %(from_date)s and %(to_date)s and gle.budget_line in %(budget_lines)s """+account_clause+" group by gle.budget_line,gle.account,acc.root_type",args,as_dict=True)
    actual_by_line={};accounts_by_line={}
    for x in actuals:
      actual_by_line[x.budget_line]=flt(actual_by_line.get(x.budget_line))+flt(x.actual_amount);accounts_by_line.setdefault(x.budget_line,[]).append(x)
    budget={n:flt(by_name[n].line_cost) for n in ordered};actual={n:flt(actual_by_line.get(n)) for n in ordered}
    for n in reversed(ordered):
      if by_name[n].is_group:
       budget[n]=sum(budget.get(c,0) for c in children.get(n,[]) if c in included);actual[n]=sum(actual.get(c,0) for c in children.get(n,[]) if c in included)
    threshold=flt(filters.get("under_utilized_threshold") or 70);rows=[]
    for n in ordered:
      b=budget[n];a=actual[n];variance=b-a;util=a*100/b if b else 0
      status="Unbudgeted Expense" if not b and a else ("Over Budget" if variance<0 else ("Fully Utilized" if util>=100 else ("Under Utilized" if util<threshold else "Within Budget")))
      accs=accounts_by_line.get(n,[]);account=accs[0].account if len(accs)==1 else None
      rows.append({"budget_line":n,"account":account,"budget_amount":b,"actual_amount":a,"variance":variance,"utilization_percentage":util,"performance_status":status,"currency":currency,"parent":by_name[n].parent_budget_line,"is_account_row":0,"is_summary_row":int(by_name[n].is_group or len(accs)>1)})
      if int(filters.get("show_account_details") if filters.get("show_account_details") is not None else 1) and not by_name[n].is_group and len(accs)>1:
       for x in sorted(accs,key=lambda z:z.account):rows.append({"budget_line":n+"::"+x.account,"account":x.account,"actual_amount":flt(x.actual_amount),"currency":currency,"parent":n,"is_account_row":1,"performance_status":_("Selected Asset Account") if x.root_type=="Asset" else _("Expense Account")})
    roots_data=[x for x in rows if not x.get("parent") and not x.get("is_account_row")];tb=sum(flt(x.get("budget_amount")) for x in roots_data);ta=sum(flt(x.get("actual_amount")) for x in roots_data);rate=ta*100/tb if tb else 0
    summary=[{"value":tb,"indicator":"Blue","label":_("Approved Budget"),"datatype":"Currency","currency":currency},{"value":ta,"indicator":"Blue","label":_("Total Actual"),"datatype":"Currency","currency":currency},{"value":tb-ta,"indicator":"Red" if ta>tb else "Green","label":_("Available Balance"),"datatype":"Currency","currency":currency},{"value":rate,"indicator":"Red" if rate>100 else "Green","label":_("Utilization Rate"),"datatype":"Percent"}]
    counts={}
    for x in rows:
      if not x.get("is_account_row"):counts[x.get("performance_status")]=counts.get(x.get("performance_status"),0)+1
    chart={"data":{"labels":list(counts),"datasets":[{"name":_("Budget Lines"),"values":list(counts.values())}]},"type":"donut","height":300}
    return finalize_report_result((columns, rows, "", chart, summary, 1))
