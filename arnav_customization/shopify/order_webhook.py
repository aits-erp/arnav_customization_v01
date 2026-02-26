import frappe
import json
import requests
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice


# =====================================================
# OLD SHOPIFY ORDERS IMPORT (FULL SAFE VERSION)
# =====================================================
@frappe.whitelist()
def sync_existing_orders_full():

    SHOP = "jewel-box-arnav.myshopify.com"
    TOKEN = "PUT_NEW_TOKEN_HERE"
    API_VERSION = "2025-04"

    HEADERS = {
        "X-Shopify-Access-Token": TOKEN,
        "Content-Type": "application/json"
    }

    res = requests.get(
        f"https://{SHOP}/admin/api/{API_VERSION}/orders.json?status=any&limit=50",
        headers=HEADERS
    ).json()

    for data in res.get("orders", []):

        shopify_id = data.get("id")

        # ===============================
        # DUPLICATE PREVENT
        # ===============================
        if frappe.db.exists("Sales Order", {"po_no": shopify_id}):
            continue

        # ===============================
        # CUSTOMER SAFE READ
        # ===============================
        customer_data = data.get("customer") or {}

        email = data.get("email") or "guest@shopify.com"
        customer_name = customer_data.get("first_name") or "Shopify Customer"

        customer = frappe.db.get_value("Customer", {"email_id": email})

        if not customer:
            c = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": customer_name,
                "customer_type": "Individual",
                "email_id": email
            })
            c.insert(ignore_permissions=True)
            customer = c.name

        # ===============================
        # SALES ORDER
        # ===============================
        so = frappe.get_doc({
            "doctype": "Sales Order",
            "customer": customer,
            "po_no": shopify_id,
            "transaction_date": frappe.utils.today(),
            "items": []
        })

        for li in data.get("line_items", []):

            sku = li.get("sku")
            qty = li.get("quantity", 1)

            rate = li.get("price") or li.get(
                "price_set", {}
            ).get("shop_money", {}).get("amount", 0)

            item_code = frappe.db.get_value(
                "SKU Details",
                {"sku": sku},
                "product"
            )

            if not item_code:
                continue

            so.append("items", {
                "item_code": item_code,
                "qty": qty,
                "rate": rate,
                "warehouse": "Arnav & Co - AAC",  # ⭐ IMPORTANT
                "sku": sku
            })

        if not so.items:
            continue

        so.insert(ignore_permissions=True)
        so.submit()

        # ===============================
        # DELIVERY NOTE (ERP SAFE)
        # ===============================
        dn = make_delivery_note(so.name)

        for d in dn.items:
            d.warehouse = "Arnav & Co - AAC"

        dn.insert(ignore_permissions=True)
        dn.submit()

        # ===============================
        # SALES INVOICE (ERP SAFE)
        # ===============================
        si = make_sales_invoice(so.name)
        si.insert(ignore_permissions=True)
        si.submit()

        # ===============================
        # PAYMENT ENTRY SAFE
        # ===============================
        pe = frappe.get_doc({
            "doctype": "Payment Entry",
            "payment_type": "Receive",
            "party_type": "Customer",
            "party": customer,
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

    frappe.db.commit()

    return "🔥 FULL Existing Shopify Orders Synced"


# =====================================================
# NEW SHOPIFY ORDER WEBHOOK (FULL SAFE VERSION)
# =====================================================
@frappe.whitelist(allow_guest=True)
def create_order():

    try:
        data = json.loads(frappe.request.data)
    except:
        return {"status": "invalid payload"}

    # ===============================
    # CUSTOMER SAFE READ
    # ===============================
    customer_data = data.get("customer") or {}

    email = data.get("email") or "guest@shopify.com"
    customer_name = customer_data.get("first_name") or "Shopify Customer"

    customer = frappe.db.get_value("Customer", {"email_id": email})

    if not customer:
        c = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_type": "Individual",
            "email_id": email
        })
        c.insert(ignore_permissions=True)
        customer = c.name

    # ===============================
    # SALES ORDER
    # ===============================
    so = frappe.get_doc({
        "doctype": "Sales Order",
        "customer": customer,
        "transaction_date": frappe.utils.today(),
        "items": []
    })

    for li in data.get("line_items", []):

        sku = li.get("sku")
        qty = li.get("quantity", 1)

        rate = li.get("price") or li.get(
            "price_set", {}
        ).get("shop_money", {}).get("amount", 0)

        item_code = frappe.db.get_value(
            "SKU Details",
            {"sku": sku},
            "product"
        )

        if not item_code:
            continue

        so.append("items", {
            "item_code": item_code,
            "qty": qty,
            "rate": rate,
            "warehouse": "Arnav & Co - AAC",
            "sku": sku
        })

    if not so.items:
        return {"status": "no items matched"}

    so.insert(ignore_permissions=True)
    so.submit()

    # DELIVERY NOTE SAFE
    dn = make_delivery_note(so.name)

    for d in dn.items:
        d.warehouse = "Arnav & Co - AAC"

    dn.insert(ignore_permissions=True)
    dn.submit()

    # SALES INVOICE SAFE
    si = make_sales_invoice(so.name)
    si.insert(ignore_permissions=True)
    si.submit()

    # PAYMENT ENTRY SAFE
    pe = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Receive",
        "party_type": "Customer",
        "party": customer,
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

    frappe.db.commit()

    return {"status": "success", "sales_order": so.name}
