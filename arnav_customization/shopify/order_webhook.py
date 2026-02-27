import frappe
import json
import requests
from frappe.utils import today, flt

# =====================================================
# SHOPIFY CONFIG
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
# GET OR CREATE CUSTOMER
# =====================================================
def get_or_create_customer(order_data):

    customer_data = order_data.get("customer") or {}
    email = order_data.get("email") or f"shopify_{order_data.get('id')}@aitsind.com"
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
# RESOLVE ITEM FROM SKU OR TITLE
# =====================================================
def resolve_item(line_item):

    sku = line_item.get("sku")
    title = line_item.get("title")

    # Try SKU Details first
    if sku:
        item_code = frappe.db.get_value("SKU Details", {"sku": sku}, "product")
        if item_code:
            return item_code, sku

    # Fallback by item name
    if title:
        item_code = frappe.db.get_value("Item", {"item_name": title}, "name")
        if item_code:
            return item_code, sku

    return None, None


# =====================================================
# BUILD SALES INVOICE (NO DELIVERY NOTE)
# =====================================================
def build_sales_invoice(order_data):

    shopify_order_id = order_data.get("id")

    # Duplicate protection
    if frappe.db.exists("Sales Invoice", {"po_no": shopify_order_id}):
        return None

    customer = get_or_create_customer(order_data)

    invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": customer,
        "company": frappe.defaults.get_user_default("Company"),
        "po_no": shopify_order_id,
        "posting_date": today(),
        "set_warehouse": WAREHOUSE,
        "update_stock": 1,   # Stock deduct directly
        "items": []
    })

    for line in order_data.get("line_items", []):

        qty = line.get("quantity", 1)
        rate = (
            line.get("price")
            or line.get("price_set", {}).get("shop_money", {}).get("amount", 0)
        )

        item_code, sku = resolve_item(line)

        if not item_code:
            continue

        batch_no = None

        # Batch = SKU logic
        if sku:

            if not frappe.db.exists("Batch", sku):
                batch = frappe.get_doc({
                    "doctype": "Batch",
                    "batch_id": sku,
                    "item": item_code
                })
                batch.insert(ignore_permissions=True)

            batch_no = sku

        invoice.append("items", {
            "item_code": item_code,
            "qty": qty,
            "rate": flt(rate),
            "warehouse": WAREHOUSE,
            "batch_no": batch_no
        })

    if not invoice.items:
        return None

    invoice.insert(ignore_permissions=True)
    invoice.submit()

    return invoice


# =====================================================
# CREATE PAYMENT ENTRY
# =====================================================
def create_payment(invoice):

    cash_account = frappe.db.get_single_value("Company", "default_cash_account")

    payment = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Receive",
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

    payment.insert(ignore_permissions=True)
    payment.submit()


# =====================================================
# IMPORT OLD SHOPIFY ORDERS
# =====================================================
@frappe.whitelist()
def sync_existing_orders_full():

    response = requests.get(
        f"https://{SHOP}/admin/api/{API_VERSION}/orders.json?status=any&limit=100",
        headers=HEADERS
    ).json()

    count = 0

    for order in response.get("orders", []):

        invoice = build_sales_invoice(order)

        if not invoice:
            continue

        create_payment(invoice)
        count += 1

    frappe.db.commit()

    return f"🔥 Imported {count} Orders (Invoice + Payment)"


# =====================================================
# SHOPIFY WEBHOOK (NEW ORDERS)
# =====================================================
@frappe.whitelist(allow_guest=True)
def create_order():

    try:
        order_data = json.loads(frappe.request.data)
    except:
        return {"status": "invalid payload"}

    invoice = build_sales_invoice(order_data)

    if not invoice:
        return {"status": "skipped"}

    create_payment(invoice)

    frappe.db.commit()

    return {"status": "success", "invoice": invoice.name}
