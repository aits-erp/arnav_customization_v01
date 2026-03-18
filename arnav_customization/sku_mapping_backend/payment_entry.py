import frappe
from frappe.model.document import Document

def calculate_custom_paid_amount(doc, method=None):
    total = 0.0

    if doc.custom_payment_details_table:
        for row in doc.custom_payment_details_table:
            if row.amount:
                total += float(row.amount)

    # Set total to standard field
    doc.paid_amount = total