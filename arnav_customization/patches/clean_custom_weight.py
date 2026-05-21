import frappe

def execute():
    if frappe.db.has_column("Sales Invoice Item", "custom_weight"):
        frappe.db.sql("""
            UPDATE `tabSales Invoice Item`
            SET custom_weight = 0
            WHERE custom_weight IS NULL
        """)
