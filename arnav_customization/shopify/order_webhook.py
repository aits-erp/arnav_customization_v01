import frappe
import json
from frappe.utils import today, flt

DEFAULT_WAREHOUSE = "Arnav & Co - AAC"
GST_TEMPLATE = "Output GST In-state - AAC"


# =====================================================
# CUSTOMER
# =====================================================

def get_or_create_customer(order_data):

    email = order_data.get("email")

    if not email:
        email = f"shopify_{order_data.get('id')}@shopify.com"

    customer = frappe.db.get_value("Customer", {"email_id": email})

    if not customer:

        doc = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": f"Shopify Customer {order_data.get('id')}",
            "customer_type": "Individual",
            "email_id": email
        })

        doc.insert(ignore_permissions=True)
        customer = doc.name

    return customer


# =====================================================
# SKU RESOLVE
# =====================================================

def resolve_item(line_item):

    sku = (line_item.get("sku") or "").strip()

    frappe.log_error(f"SKU RECEIVED: {sku}", "SHOPIFY DEBUG")

    if not sku:
        frappe.log_error("SKU EMPTY", "SHOPIFY ERROR")
        return None

    row = frappe.db.get_value(
        "SKU",
        {"sku_code": sku},
        ["product", "warehouse", "batch_no", "shopify_rate"],
        as_dict=True
    )

    if not row:
        frappe.log_error(f"SKU NOT FOUND: {sku}", "SHOPIFY ERROR")
        return None

    item_code = row.product

    if not frappe.db.exists("Item", item_code):
        frappe.log_error(f"ITEM NOT FOUND: {item_code}", "SHOPIFY ERROR")
        return None

    warehouse = row.warehouse or DEFAULT_WAREHOUSE
    batch_no = row.batch_no or sku
    rate = row.shopify_rate

    return {
        "item_code": item_code,
        "warehouse": warehouse,
        "batch_no": batch_no,
        "rate": rate
    }


# =====================================================
# SALES ORDER
# =====================================================

def build_sales_order(order_data):

    order_id = order_data.get("id")

    frappe.log_error(
        f"BUILDING SALES ORDER FOR: {order_id}",
        "SHOPIFY DEBUG"
    )

    if frappe.db.exists("Sales Order", {"po_no": order_id}):
        return None

    customer = get_or_create_customer(order_data)

    company = frappe.defaults.get_user_default("Company")

    so = frappe.get_doc({
        "doctype": "Sales Order",
        "customer": customer,
        "company": company,
        "po_no": order_id,
        "transaction_date": today(),
        "delivery_date": today(),
        "currency": "INR",
        "conversion_rate": 1,
        "selling_price_list": "Standard Selling",
        "taxes_and_charges": GST_TEMPLATE,
        "items": []
    })

    for line in order_data.get("line_items", []):

        qty = line.get("quantity", 1)

        resolved = resolve_item(line)

        if not resolved:
            continue

        rate = resolved["rate"]

        if not frappe.db.exists("Batch", {"batch_id": resolved["batch_no"]}):

            batch = frappe.get_doc({
                "doctype": "Batch",
                "batch_id": resolved["batch_no"],
                "item": resolved["item_code"]
            })

            batch.insert(ignore_permissions=True)

        so.append("items", {
            "item_code": resolved["item_code"],
            "qty": qty,
            "rate": flt(rate),
            "warehouse": resolved["warehouse"],
            "batch_no": resolved["batch_no"],
            "custom_sku": line.get("sku")
        })

    if not so.items:
        return None

    try:

        so.insert(ignore_permissions=True)
        so.submit()

        frappe.log_error(
            f"SALES ORDER CREATED: {so.name}",
            "SHOPIFY SUCCESS"
        )

        return so

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "SALES ORDER ERROR"
        )

        return None


# =====================================================
# SALES INVOICE
# =====================================================

def build_sales_invoice(order_data, sales_order):

    status = (order_data.get("financial_status") or "").lower()

    if status not in ["paid", "authorized"]:
        frappe.log_error("ORDER NOT PAID → INVOICE SKIPPED", "SHOPIFY DEBUG")
        return None

    order_id = order_data.get("id")

    invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": sales_order.customer,
        "company": sales_order.company,
        "po_no": order_id,
        "posting_date": today(),
        "update_stock": 0,
        "currency": "INR",
        "conversion_rate": 1,
        "taxes_and_charges": GST_TEMPLATE,
        "items": []
    })

    for row in sales_order.items:

        invoice.append("items", {
            "item_code": row.item_code,
            "qty": row.qty,
            "rate": row.rate,
            "warehouse": row.warehouse,
            "custom_sku": row.custom_sku,
            "batch_no": row.batch_no,
            "sales_order": sales_order.name,
            "so_detail": row.name
        })

    try:

        invoice.insert(ignore_permissions=True)
        invoice.submit()

        frappe.log_error(
            f"SALES INVOICE CREATED: {invoice.name}",
            "SHOPIFY SUCCESS"
        )

        return invoice

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "SALES INVOICE ERROR"
        )

        return None


# =====================================================
# PAYMENT ENTRY
# =====================================================

def create_payment(invoice):

    company = invoice.company

    cash_account = frappe.db.get_value(
        "Account",
        {"account_type": "Cash", "company": company},
        "name"
    )

    if not cash_account:
        frappe.log_error("CASH ACCOUNT NOT FOUND", "SHOPIFY ERROR")
        return

    payment = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Receive",
        "company": company,
        "posting_date": today(),
        "party_type": "Customer",
        "party": invoice.customer,
        "paid_to": cash_account,
        "paid_amount": invoice.grand_total,
        "received_amount": invoice.grand_total,
        "references": [{
            "reference_doctype": "Sales Invoice",
            "reference_name": invoice.name,
            "allocated_amount": invoice.grand_total
        }]
    })

    try:

        payment.insert(ignore_permissions=True)
        payment.submit()

        frappe.log_error(
            f"PAYMENT CREATED: {payment.name}",
            "SHOPIFY SUCCESS"
        )

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "PAYMENT ENTRY ERROR"
        )


# =====================================================
# WEBHOOK
# =====================================================

@frappe.whitelist(allow_guest=True)
def create_order():

    frappe.set_user("Administrator")

    try:

        order_data = frappe.request.get_json()

        frappe.log_error(
            json.dumps(order_data, indent=2),
            "SHOPIFY WEBHOOK RECEIVED"
        )

    except Exception as e:

        frappe.log_error(str(e), "SHOPIFY WEBHOOK ERROR")

        return {"status": "invalid payload"}

    sales_order = build_sales_order(order_data)

    if not sales_order:
        return {"status": "sales_order_failed"}

    invoice = build_sales_invoice(order_data, sales_order)

    if invoice:
        create_payment(invoice)

    frappe.db.commit()

    frappe.log_error(
        f"ORDER PROCESS COMPLETE: {order_data.get('id')}",
        "SHOPIFY SUCCESS"
    )

    return {
        "status": "success",
        "sales_order": sales_order.name,
        "invoice": invoice.name if invoice else None
    }


# import frappe
# import json
# from frappe.utils import today, flt


# DEFAULT_WAREHOUSE = "Arnav & Co - AAC"


# # =====================================================
# # CUSTOMER
# # =====================================================

# def get_or_create_customer(order_data):

#     email = order_data.get("email")

#     if not email:
#         email = f"shopify_{order_data.get('id')}@shopify.com"

#     frappe.log_error(f"Customer Email: {email}", "SHOPIFY DEBUG")

#     customer = frappe.db.get_value("Customer", {"email_id": email})

#     if not customer:

#         doc = frappe.get_doc({
#             "doctype": "Customer",
#             "customer_name": f"Shopify Customer {order_data.get('id')}",
#             "customer_type": "Individual",
#             "email_id": email
#         })

#         doc.insert(ignore_permissions=True)

#         customer = doc.name

#         frappe.log_error(f"Customer Created: {customer}", "SHOPIFY DEBUG")

#     else:
#         frappe.log_error(f"Customer Found: {customer}", "SHOPIFY DEBUG")

#     return customer


# # =====================================================
# # SKU → ITEM
# # =====================================================

# def resolve_item(line_item):

#     sku = (line_item.get("sku") or "").strip()

#     frappe.log_error(f"SKU RECEIVED: {sku}", "SHOPIFY DEBUG")

#     if not sku:
#         frappe.log_error("SKU EMPTY", "SHOPIFY ERROR")
#         return None

#     row = frappe.db.get_value(
#         "SKU",
#         {"sku_code": sku},
#         ["product", "warehouse", "batch_no", "shopify_rate"],
#         as_dict=True
#     )

#     if not row:
#         frappe.log_error(f"SKU NOT FOUND: {sku}", "SHOPIFY ERROR")
#         return None

#     frappe.log_error(f"SKU FOUND → Product: {row.product}", "SHOPIFY DEBUG")

#     item_code = row.product

#     if not frappe.db.exists("Item", item_code):

#         frappe.log_error(
#             f"ITEM NOT FOUND: {item_code}",
#             "SHOPIFY ERROR"
#         )

#         return None

#     warehouse = row.warehouse or DEFAULT_WAREHOUSE
#     batch_no = row.batch_no or sku
#     rate = row.shopify_rate

#     frappe.log_error(
#         f"ITEM RESOLVED → {item_code} | WH {warehouse} | Batch {batch_no}",
#         "SHOPIFY DEBUG"
#     )

#     return {
#         "item_code": item_code,
#         "warehouse": warehouse,
#         "batch_no": batch_no,
#         "rate": rate
#     }


# # =====================================================
# # SALES ORDER
# # =====================================================

# def build_sales_order(order_data):

#     order_id = order_data.get("id")

#     frappe.log_error(
#         f"BUILDING SALES ORDER FOR: {order_id}",
#         "SHOPIFY DEBUG"
#     )

#     if frappe.db.exists("Sales Order", {"po_no": order_id}):

#         frappe.log_error(
#             f"SALES ORDER ALREADY EXISTS: {order_id}",
#             "SHOPIFY DEBUG"
#         )

#         return None

#     customer = get_or_create_customer(order_data)

#     so = frappe.get_doc({
#         "doctype": "Sales Order",
#         "customer": customer,
#         "company": frappe.defaults.get_user_default("Company"),
#         "po_no": order_id,
#         "transaction_date": today(),
#         "delivery_date": today(),
#         "currency": "INR",
#         "conversion_rate": 0,
#         "items": []
#     })

#     for line in order_data.get("line_items", []):

#         qty = line.get("quantity", 1)

#         resolved = resolve_item(line)

#         if not resolved:
#             continue

#         rate = (
#             line.get("price")
#             or line.get("price_set", {})
#                 .get("shop_money", {})
#                 .get("amount", 0)
#         )

#         frappe.log_error(
#             f"ADDING ITEM → {resolved['item_code']} | Qty {qty} | Rate {rate}",
#             "SHOPIFY DEBUG"
#         )

#         if not frappe.db.exists("Batch", {"batch_id": resolved["batch_no"]}):

#             batch = frappe.get_doc({
#                 "doctype": "Batch",
#                 "batch_id": resolved["batch_no"],
#                 "item": resolved["item_code"]
#             })

#             batch.insert(ignore_permissions=True)

#             frappe.log_error(
#                 f"BATCH CREATED: {resolved['batch_no']}",
#                 "SHOPIFY DEBUG"
#             )

#         so.append("items", {
#             "item_code": resolved["item_code"],
#             "qty": qty,
#             "rate": flt(rate),
#             "warehouse": resolved["warehouse"],
#             "batch_no": resolved["batch_no"],
# 			"custom_sku": line.get("sku")
#         })

#     frappe.log_error(
#         f"ITEM COUNT IN SO: {len(so.items)}",
#         "SHOPIFY DEBUG"
#     )

#     if not so.items:

#         frappe.log_error(
#             "NO ITEMS FOUND → ORDER SKIPPED",
#             "SHOPIFY ERROR"
#         )

#         return None

#     try:

#         so.insert(ignore_permissions=True)
#         so.submit()

#         frappe.db.commit()

#         frappe.log_error(
#             f"SALES ORDER CREATED: {so.name}",
#             "SHOPIFY SUCCESS"
#         )

#         return so

#     except Exception:

#         frappe.log_error(
#             frappe.get_traceback(),
#             "SALES ORDER ERROR"
#         )

#         return None


# # =====================================================
# # SALES INVOICE
# # =====================================================

# def build_sales_invoice(order_data, sales_order):

#     if order_data.get("financial_status") != "paid":

#         frappe.log_error(
#             "ORDER NOT PAID → INVOICE SKIPPED",
#             "SHOPIFY DEBUG"
#         )

#         return None

#     order_id = order_data.get("id")

#     invoice = frappe.get_doc({
#         "doctype": "Sales Invoice",
#         "customer": sales_order.customer,
#         "company": sales_order.company,
#         "po_no": order_id,
#         "posting_date": today(),
#         "update_stock": 0,
#         "currency": "INR",
#         "conversion_rate": 1,
#         "items": []
#     })

#     for row in sales_order.items:

#         invoice.append("items", {
#             "item_code": row.item_code,
#             "qty": row.qty,
#             "rate": row.rate,
#             "warehouse": row.warehouse,
# 			"custom_sku": row.custom_sku,
#             "batch_no": row.batch_no,
#             "sales_order": sales_order.name,
#             "so_detail": row.name
#         })

#     invoice.insert(ignore_permissions=True)
#     invoice.submit()

#     frappe.log_error(
#         f"SALES INVOICE CREATED: {invoice.name}",
#         "SHOPIFY SUCCESS"
#     )

#     return invoice


# # =====================================================
# # PAYMENT ENTRY
# # =====================================================

# def create_payment(invoice):

#     company = invoice.company

#     cash_account = frappe.db.get_value(
#         "Account",
#         {"account_type": "Cash", "company": company},
#         "name"
#     )

#     frappe.log_error(
#         f"CASH ACCOUNT: {cash_account}",
#         "SHOPIFY DEBUG"
#     )

#     if not cash_account:
#         frappe.log_error(
#             "CASH ACCOUNT NOT FOUND",
#             "SHOPIFY PAYMENT ERROR"
#         )
#         return

#     payment = frappe.get_doc({
#         "doctype": "Payment Entry",
#         "payment_type": "Receive",
#         "company": company,
#         "posting_date": today(),
#         "party_type": "Customer",
#         "party": invoice.customer,
#         "paid_to": cash_account,
#         "paid_amount": invoice.grand_total,
#         "received_amount": invoice.grand_total,
#         "references": [{
#             "reference_doctype": "Sales Invoice",
#             "reference_name": invoice.name,
#             "allocated_amount": invoice.grand_total
#         }]
#     })

#     payment.insert(ignore_permissions=True)
#     payment.submit()

#     frappe.log_error(
#         f"PAYMENT CREATED: {payment.name}",
#         "SHOPIFY SUCCESS"
#     )


# # =====================================================
# # WEBHOOK
# # =====================================================

# @frappe.whitelist(allow_guest=True)
# def create_order():

#     frappe.set_user("Administrator")

#     try:

#         order_data = frappe.request.get_json()

#         frappe.log_error(
#             json.dumps(order_data, indent=2),
#             "SHOPIFY WEBHOOK RECEIVED"
#         )

#     except Exception as e:

#         frappe.log_error(str(e), "SHOPIFY WEBHOOK ERROR")

#         return {"status": "invalid payload"}

#     sales_order = build_sales_order(order_data)

#     if not sales_order:
#         return {"status": "skipped"}

#     invoice = build_sales_invoice(order_data, sales_order)

#     if invoice:
#         create_payment(invoice)

#     frappe.db.commit()

#     frappe.log_error(
#         f"ORDER PROCESS COMPLETE: {order_data.get('id')}",
#         "SHOPIFY SUCCESS"
#     )

#     return {
#         "status": "success",
#         "sales_order": sales_order.name,
#         "invoice": invoice.name if invoice else None
#     }

