import frappe

def execute():
    # Convert NULL to 0
    frappe.db.sql("""
        UPDATE `tabSales Invoice Item`
        SET custom_weight = 0
        WHERE custom_weight IS NULL
    """)

    # Convert empty string to 0
    frappe.db.sql("""
        UPDATE `tabSales Invoice Item`
        SET custom_weight = 0
        WHERE custom_weight = ''
    """)
