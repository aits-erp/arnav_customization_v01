import frappe
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
import json
import requests


@frappe.whitelist(allow_guest=True)
def sync_existing_orders_full():

    SHOP = "jewel-box-arnav.myshopify.com"
    TOKEN = "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"
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

        # ⭐ Duplicate prevent
        if frappe.db.exists("Sales Order", {"po_no": shopify_id}):
            continue

        email = data.get("email") or "guest@shopify.com"
        customer_name = data.get("customer", {}).get("first_name", "Shopify Customer")

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

            rate = li.get("price") or li.get("price_set", {}).get("shop_money", {}).get("amount", 0)

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
                "warehouse": "Arnav & Co - AAC",  # change if needed
                "sku": sku
            })

        if not so.items:
            continue

        so.insert(ignore_permissions=True)
        so.submit()

        # ===============================
        # DELIVERY NOTE (SAFE)
        # ===============================
        dn = make_delivery_note(so.name)
        dn.insert(ignore_permissions=True)
        dn.submit()

        # ===============================
        # SALES INVOICE (SAFE)
        # ===============================
        si = make_sales_invoice(so.name)
        si.insert(ignore_permissions=True)
        si.submit()

        # ===============================
        # PAYMENT ENTRY (LINKED)
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

@frappe.whitelist(allow_guest=True)
def create_order():

    # ⭐ UNIVERSAL PAYLOAD READER (Fix for Unsupported Media Type)
    try:
        raw = frappe.request.data
        data = json.loads(raw)
    except:
        return {"status": "invalid payload"}

    # ===============================
    # CUSTOMER
    # ===============================
    email = data.get("email") or "guest@shopify.com"
    customer_name = data.get("customer", {}).get("first_name", "Shopify Customer")

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

        # ⭐ UNIVERSAL PRICE SUPPORT (2024/2025/2026)
        rate = li.get("price") or li.get("price_set", {}).get("shop_money", {}).get("amount", 0)

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
            "sku": sku
        })

    if not so.items:
        return {"status": "no items matched"}

    so.insert(ignore_permissions=True)
    so.submit()

    # ===============================
    # DELIVERY NOTE
    # ===============================
    dn = frappe.get_doc({
        "doctype": "Delivery Note",
        "customer": customer,
        "items": so.items
    })

    dn.insert(ignore_permissions=True)
    dn.submit()

    # ===============================
    # SALES INVOICE
    # ===============================
    si = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": customer,
        "items": so.items
    })

    si.insert(ignore_permissions=True)
    si.submit()

    # ===============================
    # PAYMENT ENTRY
    # ===============================
    pe = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Receive",
        "party_type": "Customer",
        "party": customer,
        "paid_amount": si.grand_total,
        "received_amount": si.grand_total
    })

    pe.insert(ignore_permissions=True)
    pe.submit()

    frappe.db.commit()

    return {"status": "success", "sales_order": so.name}
