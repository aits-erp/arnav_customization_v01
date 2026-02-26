import frappe
import json
import requests
from frappe.utils import today, add_days
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note, make_sales_invoice


# =====================================================
# GLOBAL CONFIG
# =====================================================
SHOP = "jewel-box-arnav.myshopify.com"
TOKEN = "PUT_NEW_TOKEN_HERE"
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
    customer_name = customer_data.get("first_name") or "Shopify Customer"

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
# CREATE SALES ORDER CORE ENGINE
# =====================================================
def build_sales_order(data):

    shopify_id = data.get("id")

    # Duplicate Protection
    if frappe.db.exists("Sales Order", {"po_no": shopify_id}):
        return None

    customer = get_or_create_customer(data)

    so = frappe.get_doc({
        "doctype": "Sales Order",
        "customer": customer,
        "po_no": shopify_id,
        "transaction_date": today(),
        "delivery_date": add_days(today(), 1),
        "items": []
    })

    for li in data.get("line_items", []):

        sku = li.get("sku")
        qty = li.get("quantity", 1)

        rate = (
            li.get("price")
            or li.get("price_set", {}).get("shop_money", {}).get("amount", 0)
        )

        if not sku:
            continue

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
            "warehouse": WAREHOUSE,
            "sku": sku
        })

    if not so.items:
        return None

    so.insert(ignore_permissions=True)
    so.submit()

    return so


# =====================================================
# CREATE DN + INVOICE + PAYMENT (ERP SAFE)
# =====================================================
def create_documents(so):

    # DELIVERY NOTE
    dn = make_delivery_note(so.name)

    for d in dn.items:
        d.warehouse = WAREHOUSE

    dn.insert(ignore_permissions=True)
    dn.submit()

    # SALES INVOICE
    si = make_sales_invoice(so.name)
    si.insert(ignore_permissions=True)
    si.submit()

    # PAYMENT ENTRY
    pe = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Receive",
        "party_type": "Customer",
        "party": so.customer,
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
# OLD SHOPIFY ORDERS IMPORT
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

    return f"🔥 Imported {count} Shopify Orders Successfully"


# =====================================================
# NEW ORDER WEBHOOK
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

    return {"status": "success", "sales_order": so.name}
