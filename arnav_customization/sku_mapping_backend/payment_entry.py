import frappe
from frappe.model.document import Document

def calculate_custom_paid_amount(doc, method=None):
    total = 0.0

    if doc.custom_payment_details_table:
        for row in doc.custom_payment_details_table:
            if row.amount:
                total += float(row.amount)

    # ================================
    # SAFE OVERRIDE ONLY IF READY
    # ================================
    if doc.doctype == "Payment Entry":

        if not doc.paid_from_account_currency or not doc.paid_to_account_currency:
            frappe.log_error(
                "Skipped paid_amount override: currency not set",
                "Payment Entry Safe Guard"
            )
            return

        try:
            doc.paid_amount = total
            doc.received_amount = total
        except Exception as e:
            frappe.log_error(str(e), "Payment Entry Override Failed")
    total = 0.0

    if doc.custom_payment_details_table:
        for row in doc.custom_payment_details_table:
            if row.amount:
                total += float(row.amount)

    # ✅ Only apply AFTER doc is stable
    if doc.doctype == "Payment Entry":
        if doc.paid_from_account_currency and doc.paid_to_account_currency:
            doc.paid_amount = total
            doc.received_amount = total