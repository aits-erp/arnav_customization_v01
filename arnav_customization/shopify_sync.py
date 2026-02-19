import frappe
import requests

SHOP = "jewel-box-arnav.myshopify.com"
TOKEN = "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"
API_VERSION = "2024-01"

HEADERS = {
    "X-Shopify-Access-Token": TOKEN,
    "Content-Type": "application/json"
}

def sync_to_shopify(doc, method=None):

    # ✅ 1. Create Shopify Product
    product_payload = {
        "product": {
            "title": doc.product,
            "status": "active"
        }
    }

    res = requests.post(
        f"https://{SHOP}/admin/api/{API_VERSION}/products.json",
        json=product_payload,
        headers=HEADERS
    )

    product_id = res.json()["product"]["id"]

    # ✅ 2. Create Variants from SKU Details
    for d in doc.sku_details:

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

        inventory_item_id = v["variant"]["inventory_item_id"]

        # ✅ 3. Update Inventory
        inventory_payload = {
            "location_id": 52386005145,
            "inventory_item_id": inventory_item_id,
            "available": d.qty
        }

        requests.post(
            f"https://{SHOP}/admin/api/{API_VERSION}/inventory_levels/set.json",
            json=inventory_payload,
            headers=HEADERS
        )

    frappe.msgprint("✅ Shopify Sync Done")
