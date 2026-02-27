import frappe
import json
import requests
from frappe.utils import today, add_days, flt
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note, make_sales_invoice

# =====================================================
# CONFIG
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
# CUSTOMER
# =====================================================
def get_or_create_customer(data):

    customer_data = data.get("customer") or {}
    email = data.get("email") or f"shopify_{data.get('id')}@aitsind.com"
    name = customer_data.get("first_name") or "Shopify Customer"

    customer = frappe.db.get_value("Customer", {"email_id": email})

    if not customer:
        doc = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": name,
            "customer_type": "Individual",
            "email_id": email
        })
        doc.insert(ignore_permissions=True)
        customer = doc.name

    return customer


# =====================================================
# RESOLVE ITEM (SKU → Product)
# =====================================================
def resolve_item(li):

    sku = li.get("sku")
    title = li.get("title")

    if sku:
        item = frappe.db.get_value("SKU Details", {"sku": sku}, "product")
        if item:
            return item, sku

    if title:
        item = frappe.db.get_value("Item", {"item_name": title}, "name")
        if item:
            return item, sku

    return None, None


# =====================================================
# BUILD SALES ORDER
# =====================================================
def build_sales_order(data):

    shopify_id = data.get("id")

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
        rate = li.get("price") or li.get("price_set", {}).get("shop_money", {}).get("amount", 0)

        item_code, sku = resolve_item(li)

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
        return None

    so.insert(ignore_permissions=True)
    so.submit()

    return so


# =====================================================
# CREATE DN + INVOICE + PAYMENT
# =====================================================
def create_documents(so):

    dn = make_delivery_note(so.name)

    # Map SKU from SO
    sku_map = {i.item_code: i.sku for i in so.items if i.get("sku")}

    for d in dn.items:

        d.warehouse = WAREHOUSE

        sku = sku_map.get(d.item_code)

        if sku:

            # Create Batch if not exists
            if not frappe.db.exists("Batch", sku):
                batch = frappe.get_doc({
                    "doctype": "Batch",
                    "batch_id": sku,
                    "item": d.item_code
                })
                batch.insert(ignore_permissions=True)

            d.batch_no = sku

    dn.insert(ignore_permissions=True)
    dn.submit()

    # INVOICE
    si = make_sales_invoice(so.name)
    si.insert(ignore_permissions=True)
    si.submit()

    # PAYMENT
    cash_account = frappe.db.get_single_value("Company", "default_cash_account")

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
# IMPORT OLD SHOPIFY ORDERS
# =====================================================
@frappe.whitelist()
def sync_existing_orders_full():

    res = requests.get(
        f"https://{SHOP}/admin/api/{API_VERSION}/orders.json?status=any&limit=100",
        headers=HEADERS
    ).json()

    count = 0

    for order in res.get("orders", []):

        so = build_sales_order(order)

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
