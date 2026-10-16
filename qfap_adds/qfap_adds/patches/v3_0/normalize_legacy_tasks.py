import frappe

def execute():
    for row in frappe.get_all("Task",fields=["name","custom_assign_to","custom_user_id"],limit_page_length=100000):
        if row.custom_assign_to and not row.custom_user_id:
            user=frappe.db.get_value("Employee",row.custom_assign_to,"user_id")
            if user:frappe.db.set_value("Task",row.name,"custom_user_id",user,update_modified=False)
