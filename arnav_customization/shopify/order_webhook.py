import frappe
import json
import requests
from frappe.utils import today, add_days, flt
from erpnext.selling.doctype.sales_order.sales_order import (
    make_delivery_note,
    make_sales_invoice
)

# =====================================================
# GLOBAL CONFIG
# =====================================================
SHOP = "jewel-box-arnav.myshopify.com"
TOKEN = "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"
API_VERSION = "2025-04"
WAREHOUSE = "Arnav & Co - AAC"

HEADERS = {
    "X-Shopify-Access-Token": TOKEN,
    "Content-Type": "application/json"
}

# =====================================================
# SAFE CUSTOMER CREATOR
# =====================================================
def get_or_create_customer(data):

    customer_data = data.get("customer") or {}

    email = data.get("email") or f"shopify_{data.get('id')}@aitsind.com"
    customer_name = (
        customer_data.get("first_name")
        or customer_data.get("last_name")
        or "Shopify Customer"
    )

    customer = frappe.db.get_value("Customer", {"email_id": email})

    if not customer:
        doc = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_type": "Individual",
            "email_id": email
        })
        doc.insert(ignore_permissions=True)
        customer = doc.name

    return customer


# =====================================================
# SKU RESOLVER (JEWELLERY SAFE)
# =====================================================
def resolve_item_code(li):

    sku = li.get("sku")
    title = li.get("title")

    # 1️⃣ Exact SKU match from SKU Details
    if sku:
        item_code = frappe.db.get_value(
            "SKU Details",
            {"sku": sku},
            "product"
        )
        if item_code:
            return item_code, sku

    # 2️⃣ Fallback → Item Name match
    if title:
        item_code = frappe.db.get_value(
            "Item",
            {"item_name": title},
            "name"
        )
        if item_code:
            return item_code, sku

    # 3️⃣ Skip if not found
    frappe.log_error(f"Item not found for {title}", "SKU Mapping Failed")
    return None, None


# =====================================================
# CREATE SALES ORDER
# =====================================================
def build_sales_order(data):

    shopify_id = data.get("id")

    # Duplicate protection
    if frappe.db.exists("Sales Order", {"po_no": shopify_id}):
        return None

    customer = get_or_create_customer(data)

    so = frappe.get_doc({
        "doctype": "Sales Order",
        "customer": customer,
        "company": frappe.defaults.get_user_default("Company"),
        "po_no": shopify_id,
        "transaction_date": today(),
        "delivery_date": add_days(today(), 1),
        "items": []
    })

    for li in data.get("line_items", []):

        qty = li.get("quantity", 1)
        rate = (
            li.get("price")
            or li.get("price_set", {}).get("shop_money", {}).get("amount", 0)
        )

        item_code, sku = resolve_item_code(li)

        if not item_code:
            continue

        so.append("items", {
            "item_code": item_code,
            "qty": qty,
            "rate": flt(rate),
            "warehouse": WAREHOUSE,
            "sku": sku
        })

    if not so.items:
        frappe.log_error(
            f"No valid items for Order {shopify_id}",
            "Order Skipped"
        )
        return None

    so.insert(ignore_permissions=True)
    so.submit()

    return so


# =====================================================
# INVOICE ONLY (SAFE)
# =====================================================
def create_invoice_only(so):

    si = make_sales_invoice(so.name)
    si.insert(ignore_permissions=True)
    si.submit()

    cash_account = frappe.db.get_single_value(
        "Company",
        "default_cash_account"
    )

    pe = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Receive",
        "party_type": "Customer",
        "party": so.customer,
        "paid_to": cash_account,
        "paid_amount": si.grand_total,
        "received_amount": si.grand_total,
        "references": [{
            "reference_doctype": "Sales Invoice",
            "reference_name": si.name,
            "allocated_amount": si.grand_total
        }]
    })

    pe.insert(ignore_permissions=True)
    pe.submit()


# =====================================================
# DELIVERY NOTE + INVOICE (JEWELLERY SAFE)
# =====================================================
def create_documents(so):

    try:
        dn = make_delivery_note(so.name)

        for d in dn.items:
            d.warehouse = WAREHOUSE

            item_doc = frappe.get_doc("Item", d.item_code)

            # ==========================
            # 🔥 BATCH LOGIC
            # ==========================
            if item_doc.has_batch_no:

                sku = d.get("sku")

                if sku:

                    batch_name = frappe.db.get_value(
                        "Batch",
                        {
                            "batch_id": sku,
                            "item": d.item_code
                        },
                        "name"
                    )

                    if not batch_name:
                        if frappe.db.exists("Batch", sku):
                            batch_name = sku

                    if not batch_name:
                        batch = frappe.get_doc({
                            "doctype": "Batch",
                            "batch_id": sku,
                            "item": d.item_code
                        })
                        batch.insert(ignore_permissions=True)
                        batch_name = batch.name

                    d.batch_no = batch_name

                else:
                    frappe.log_error(
                        f"Batch required but SKU missing for {d.item_code}",
                        "Batch Missing"
                    )

            # ==========================
            # 🔥 SERIAL CHECK
            # ==========================
            if item_doc.has_serial_no:
                frappe.log_error(
                    f"Serial required for {d.item_code}. Skipping DN.",
                    "Serial Required"
                )
                return create_invoice_only(so)

        dn.insert(ignore_permissions=True)
        dn.submit()

    except Exception as e:
        frappe.log_error(str(e), "Delivery Note Failed")
        return create_invoice_only(so)

    # If DN success → create invoice
    create_invoice_only(so)


# =====================================================
# SYNC OLD ORDERS
# =====================================================
@frappe.whitelist()
def sync_existing_orders_full():

    res = requests.get(
        f"https://{SHOP}/admin/api/{API_VERSION}/orders.json?status=any&limit=50",
        headers=HEADERS
    ).json()

    count = 0

    for data in res.get("orders", []):
        so = build_sales_order(data)

        if not so:
            continue

        create_documents(so)
        count += 1

    frappe.db.commit()

    return f"✅ IMPORT DONE → {count} Orders"


# =====================================================
# SHOPIFY WEBHOOK
# =====================================================
@frappe.whitelist(allow_guest=True)
def create_order():

    try:
        data = json.loads(frappe.request.data)
    except:
        return {"status": "invalid payload"}

    so = build_sales_order(data)

    if not so:
        return {"status": "skipped"}

    create_documents(so)

    frappe.db.commit()

    return {
        "status": "success",
        "sales_order": so.name
    }


# import frappe
# import json
# import requests
# from frappe.utils import today, add_days
# from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note, make_sales_invoice


# # =====================================================
# # GLOBAL CONFIG
# # =====================================================
# SHOP = "jewel-box-arnav.myshopify.com"
# TOKEN = "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"
# API_VERSION = "2025-04"
# WAREHOUSE = "Arnav & Co - AAC"


# HEADERS = {
#     "X-Shopify-Access-Token": TOKEN,
#     "Content-Type": "application/json"
# }


# # =====================================================
# # SAFE CUSTOMER CREATOR
# # =====================================================
# def get_or_create_customer(data):

#     customer_data = data.get("customer") or {}

#     email = data.get("email") or f"shopify_{data.get('id')}@aitsind.com"
#     customer_name = customer_data.get("first_name") or "Shopify Customer"

#     customer = frappe.db.get_value("Customer", {"email_id": email})

#     if not customer:
#         doc = frappe.get_doc({
#             "doctype": "Customer",
#             "customer_name": customer_name,
#             "customer_type": "Individual",
#             "email_id": email
#         })
#         doc.insert(ignore_permissions=True)
#         customer = doc.name

#     return customer


# # =====================================================
# # CREATE SALES ORDER CORE ENGINE
# # =====================================================
# def build_sales_order(data):

#     shopify_id = data.get("id")

#     # Duplicate Protection
#     if frappe.db.exists("Sales Order", {"po_no": shopify_id}):
#         return None

#     customer = get_or_create_customer(data)

#     so = frappe.get_doc({
#         "doctype": "Sales Order",
#         "customer": customer,
#         "po_no": shopify_id,
#         "transaction_date": today(),
#         "delivery_date": add_days(today(), 1),
#         "items": []
#     })

#     for li in data.get("line_items", []):

#         sku = li.get("sku")
#         qty = li.get("quantity", 1)

#         rate = (
#             li.get("price")
#             or li.get("price_set", {}).get("shop_money", {}).get("amount", 0)
#         )

#         if not sku:
#             continue

#         item_code = frappe.db.get_value(
#             "SKU Details",
#             {"sku": sku},
#             "product"
#         )

#         if not item_code:
#             continue

#         so.append("items", {
#             "item_code": item_code,
#             "qty": qty,
#             "rate": rate,
#             "warehouse": WAREHOUSE,
#             "sku": sku
#         })

#     if not so.items:
#         return None

#     so.insert(ignore_permissions=True)
#     so.submit()

#     return so


# # =====================================================
# # CREATE DN + INVOICE + PAYMENT (ERP SAFE)
# # =====================================================
# def create_documents(so):

#     # DELIVERY NOTE
#     dn = make_delivery_note(so.name)

#     for d in dn.items:
#         d.warehouse = WAREHOUSE

#     dn.insert(ignore_permissions=True)
#     dn.submit()

#     # SALES INVOICE
#     si = make_sales_invoice(so.name)
#     si.insert(ignore_permissions=True)
#     si.submit()

#     # PAYMENT ENTRY
#     pe = frappe.get_doc({
#         "doctype": "Payment Entry",
#         "payment_type": "Receive",
#         "party_type": "Customer",
#         "party": so.customer,
#         "paid_amount": si.grand_total,
#         "received_amount": si.grand_total,
#         "references": [{
#             "reference_doctype": "Sales Invoice",
#             "reference_name": si.name,
#             "allocated_amount": si.grand_total
#         }]
#     })

#     pe.insert(ignore_permissions=True)
#     pe.submit()


# # =====================================================
# # OLD SHOPIFY ORDERS IMPORT
# # =====================================================
# @frappe.whitelist()
# def sync_existing_orders_full():

#     res = requests.get(
#         f"https://{SHOP}/admin/api/{API_VERSION}/orders.json?status=any&limit=50",
#         headers=HEADERS
#     ).json()

#     count = 0

#     for data in res.get("orders", []):

#         so = build_sales_order(data)

#         if not so:
#             continue

#         create_documents(so)
#         count += 1

#     frappe.db.commit()

#     return f"🔥 Imported {count} Shopify Orders Successfully"


# # =====================================================
# # NEW ORDER WEBHOOK
# # =====================================================
# @frappe.whitelist(allow_guest=True)
# def create_order():

#     try:
#         data = json.loads(frappe.request.data)
#     except:
#         return {"status": "invalid payload"}

#     so = build_sales_order(data)

#     if not so:
#         return {"status": "skipped"}

#     create_documents(so)

#     frappe.db.commit()

#     return {"status": "success", "sales_order": so.name}
