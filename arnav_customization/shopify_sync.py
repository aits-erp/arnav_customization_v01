import frappe
import requests

SHOP = "jewel-box-arnav.myshopify.com"
TOKEN = "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"   # ⚠️ must start with shpat_
API_VERSION = "2024-01"

HEADERS = {
    "X-Shopify-Access-Token": TOKEN,
    "Content-Type": "application/json"
}

LOCATION_ID = 52386005145


# ================================
# HELPER: GET PRODUCT BY TITLE
# ================================
def get_shopify_product_by_title(title):
    url = f"https://{SHOP}/admin/api/{API_VERSION}/products.json?title={title}"
    res = requests.get(url, headers=HEADERS).json()

    if res.get("products"):
        return res["products"][0]["id"]
    return None


# ================================
# HELPER: GET VARIANT BY SKU
# ================================
def get_variant_by_sku(sku):
    url = f"https://{SHOP}/admin/api/{API_VERSION}/variants.json?sku={sku}"
    res = requests.get(url, headers=HEADERS).json()

    if res.get("variants"):
        return res["variants"][0]
    return None


# ================================
# MAIN SYNC FUNCTION
# ================================
def sync_to_shopify(doc, method=None):

    if not doc.sku_details:
        frappe.throw("No SKU Details found")

    product_title = doc.sku_details[0].product

    # ✅ 1. CHECK PRODUCT EXISTS
    product_id = get_shopify_product_by_title(product_title)

    if not product_id:
        product_payload = {
            "product": {
                "title": product_title,
                "status": "active"
            }
        }

        res = requests.post(
            f"https://{SHOP}/admin/api/{API_VERSION}/products.json",
            json=product_payload,
            headers=HEADERS
        ).json()

        if "product" not in res:
            frappe.throw(f"Shopify Product Error: {res}")

        product_id = res["product"]["id"]

    # ✅ 2. LOOP SKU DETAILS
    for d in doc.sku_details:

        existing_variant = get_variant_by_sku(d.sku)

        # ========================
        # CREATE VARIANT
        # ========================
        if not existing_variant:

            variant_payload = {
                "variant": {
                    "product_id": product_id,
                    "sku": d.sku,
                    "price": d.selling_price,
                    "inventory_management": "shopify"
                }
            }

            v = requests.post(
                f"https://{SHOP}/admin/api/{API_VERSION}/variants.json",
                json=variant_payload,
                headers=HEADERS
            ).json()

            if "variant" not in v:
                frappe.throw(f"Variant Create Error: {v}")

            inventory_item_id = v["variant"]["inventory_item_id"]

        # ========================
        # UPDATE EXISTING VARIANT
        # ========================
        else:

            inventory_item_id = existing_variant["inventory_item_id"]

            update_payload = {
                "variant": {
                    "id": existing_variant["id"],
                    "price": d.selling_price
                }
            }

            requests.put(
                f"https://{SHOP}/admin/api/{API_VERSION}/variants/{existing_variant['id']}.json",
                json=update_payload,
                headers=HEADERS
            )

        # ========================
        # INVENTORY UPDATE
        # ========================
        inventory_payload = {
            "location_id": LOCATION_ID,
            "inventory_item_id": inventory_item_id,
            "available": d.qty
        }

        inv_res = requests.post(
            f"https://{SHOP}/admin/api/{API_VERSION}/inventory_levels/set.json",
            json=inventory_payload,
            headers=HEADERS
        ).json()

        if inv_res.get("errors"):
            frappe.throw(f"Inventory Error: {inv_res}")

    frappe.msgprint("✅ Shopify Sync Completed (Safe Mode)")
