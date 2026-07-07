# import frappe
# from frappe.model.document import Document

# def calculate_custom_paid_amount(doc, method=None):
#     total = 0.0

#     if doc.custom_payment_details_table:
#         for row in doc.custom_payment_details_table:
#             if row.amount:
#                 total += float(row.amount)

#     # ================================
#     # SAFE OVERRIDE ONLY IF READY
#     # ================================
#     if doc.doctype == "Payment Entry":

#         if not doc.paid_from_account_currency or not doc.paid_to_account_currency:
#             frappe.log_error(
#                 "Skipped paid_amount override: currency not set",
#                 "Payment Entry Safe Guard"
#             )
#             return

#         try:
#             doc.paid_amount = total
#             doc.received_amount = total
#         except Exception as e:
#             frappe.log_error(str(e), "Payment Entry Override Failed")
#     total = 0.0

#     if doc.custom_payment_details_table:
#         for row in doc.custom_payment_details_table:
#             if row.amount:
#                 total += float(row.amount)

#     # ✅ Only apply AFTER doc is stable
#     if doc.doctype == "Payment Entry":
#         if doc.paid_from_account_currency and doc.paid_to_account_currency:
#             doc.paid_amount = total
#             doc.received_amount = total


# import frappe
# from frappe.model.document import Document

# def calculate_custom_paid_amount(doc, method=None):
#     total = 0.0

#     if doc.custom_payment_details_table:
#         for row in doc.custom_payment_details_table:
#             if row.amount:
#                 total += float(row.amount)

#     # ================================
#     # SAFE OVERRIDE ONLY IF READY
#     # ================================
#     if doc.doctype == "Payment Entry":

#         if not doc.paid_from_account_currency or not doc.paid_to_account_currency:
#             frappe.log_error(
#                 "Skipped paid_amount override: currency not set",
#                 "Payment Entry Safe Guard"
#             )
#             return

#         try:
#             doc.paid_amount = total
#             doc.received_amount = total
#         except Exception as e:
#             frappe.log_error(str(e), "Payment Entry Override Failed")
#     total = 0.0

#     if doc.custom_payment_details_table:
#         for row in doc.custom_payment_details_table:
#             if row.amount:
#                 total += float(row.amount)

#     # ✅ Only apply AFTER doc is stable
#     if doc.doctype == "Payment Entry":
#         if doc.paid_from_account_currency and doc.paid_to_account_currency:
#             doc.paid_amount = total
#             doc.received_amount = total


# # ================================
# # ADDED: Block submit unless Amount = Paid Amount
# # ================================
# def validate_payment_amount_match(doc, method=None):
#     if doc.doctype != "Payment Entry":
#         return

#     total = 0.0
#     if doc.custom_payment_details_table:
#         for row in doc.custom_payment_details_table:
#             if row.amount:
#                 total += float(row.amount)

#     table_total = round(total, 2)
#     paid_amount = round(float(doc.paid_amount or 0), 2)

#     if table_total != paid_amount:
#         frappe.throw(
#             f"Amount and Paid Amount must be the same.<br>"
#             f"Total Amount: <b>{table_total}</b><br>"
#             f"Paid Amount: <b>{paid_amount}</b><br>"
#             f"Please make them equal before submitting.",
#             title="Amount Mismatch"
#         )

import frappe
from frappe.utils import flt


def calculate_custom_paid_amount(doc, method=None):
    if doc.doctype != "Payment Entry":
        return

    total = 0.0

    for row in doc.custom_payment_details_table or []:
        total += flt(row.amount)

    if not doc.paid_from_account_currency or not doc.paid_to_account_currency:
        frappe.log_error(
            "Skipped paid_amount override: currency not set",
            "Payment Entry Safe Guard"
        )
        return

    doc.paid_amount = total
    doc.received_amount = total


def validate_payment_amount_match(doc, method=None):
    if doc.doctype != "Payment Entry":
        return

    total = 0.0

    for row in doc.custom_payment_details_table or []:
        total += flt(row.amount)

    table_total = flt(total, 2)
    paid_amount = flt(doc.paid_amount, 2)

    if table_total != paid_amount:
        frappe.throw(
            f"Amount and Paid Amount must be the same.<br>"
            f"Total Amount: <b>{table_total}</b><br>"
            f"Paid Amount: <b>{paid_amount}</b><br>"
            f"Please make them equal before submitting.",
            title="Amount Mismatch"
        )