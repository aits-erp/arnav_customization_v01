import frappe
import requests

SHOP = "jewel-box-arnav.myshopify.com"
TOKEN = "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"
API_VERSION = "2024-01"

HEADERS = {
    "X-Shopify-Access-Token": TOKEN,
    "Content-Type": "application/json"
}

LOCATION_ID = 52386005145


# ===============================
# HELPER: GET PRODUCT
# ===============================
def get_product(product_id):
    res = requests.get(
        f"https://{SHOP}/admin/api/{API_VERSION}/products/{product_id}.json",
        headers=HEADERS
    )
    return res.json()


# ===============================
# HELPER: GET VARIANTS OF PRODUCT
# ===============================
def get_product_variants(product_id):
    res = requests.get(
        f"https://{SHOP}/admin/api/{API_VERSION}/products/{product_id}/variants.json",
        headers=HEADERS
    )
    return res.json().get("variants", [])


# ===============================
# MAIN SYNC FUNCTION
# ===============================
def sync_to_shopify(doc, method=None):

    if not doc.sku_details:
        frappe.throw("No SKU Details found")

    shopify_product_id = doc.sku_details[0].product
    product_id = None

    # ===============================
    # 1️⃣ CHECK EXISTING PRODUCT
    # ===============================
    if shopify_product_id:
        data = get_product(shopify_product_id)
        if data.get("product"):
            product_id = shopify_product_id

    # ===============================
    # 2️⃣ CREATE PRODUCT IF NOT EXIST
    # ===============================
    if not product_id:

        product_title = doc.sku_details[0].product

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
        )

        data = res.json()

        if "product" not in data:
            frappe.throw(f"Shopify Product Error: {data}")

        product_id = data["product"]["id"]

    # ===============================
    # 3️⃣ AUTO UNARCHIVE PRODUCT
    # ===============================
    requests.put(
        f"https://{SHOP}/admin/api/{API_VERSION}/products/{product_id}.json",
        json={"product": {"id": product_id, "status": "active"}},
        headers=HEADERS
    )

    # ===============================
    # 4️⃣ GET EXISTING VARIANTS
    # ===============================
    existing_variants = get_product_variants(product_id)

    # ===============================
    # 5️⃣ CREATE / UPDATE VARIANTS
    # ===============================
    for d in doc.sku_details:

        existing_variant = None

        for v in existing_variants:
            if v.get("sku") == d.sku:
                existing_variant = v
                break

        # ---------------------------
        # UPDATE VARIANT
        # ---------------------------
        if existing_variant:

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

        # ---------------------------
        # CREATE VARIANT
        # ---------------------------
        else:

            variant_payload = {
                "variant": {
                    "sku": d.sku,
                    "price": d.selling_price,
                    "inventory_management": "shopify"
                }
            }

            v = requests.post(
                f"https://{SHOP}/admin/api/{API_VERSION}/products/{product_id}/variants.json",
                json=variant_payload,
                headers=HEADERS
            ).json()

            if "variant" not in v:
                frappe.throw(f"Variant Error: {v}")

            inventory_item_id = v["variant"]["inventory_item_id"]

        # ---------------------------
        # INVENTORY UPDATE
        # ---------------------------
        inventory_payload = {
            "location_id": LOCATION_ID,
            "inventory_item_id": inventory_item_id,
            "available": d.qty
        }

        inv = requests.post(
            f"https://{SHOP}/admin/api/{API_VERSION}/inventory_levels/set.json",
            json=inventory_payload,
            headers=HEADERS
        ).json()

        if inv.get("errors"):
            frappe.throw(f"Inventory Error: {inv}")

    frappe.msgprint("🔥 Shopify Sync Complete (FINAL SAFE VERSION)")






# import frappe
# import requests

# SHOP = "jewel-box-arnav.myshopify.com"
# TOKEN = "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"   # ⚠️ must be shpat_
# API_VERSION = "2024-01"

# HEADERS = {
#     "X-Shopify-Access-Token": TOKEN,
#     "Content-Type": "application/json"
# }

# LOCATION_ID = 52386005145


# # ===============================
# # MAIN SYNC FUNCTION
# # ===============================
# def sync_to_shopify(doc, method=None):

#     if not doc.sku_details:
#         frappe.throw("No SKU Details found")

#     # 👉 ERP field may contain existing Shopify Product ID
#     shopify_product_id = doc.sku_details[0].product

#     # ======================================
#     # 1️⃣ CHECK IF PRODUCT EXISTS IN SHOPIFY
#     # ======================================
#     product_id = None

#     if shopify_product_id:
#         # Try to fetch existing product
#         res = requests.get(
#             f"https://{SHOP}/admin/api/{API_VERSION}/products/{shopify_product_id}.json",
#             headers=HEADERS
#         )

#         data = res.json()

#         if data.get("product"):
#             product_id = shopify_product_id

#     # ======================================
#     # 2️⃣ IF NOT EXISTS → CREATE NEW PRODUCT
#     # ======================================
#     if not product_id:

#         product_title = f"{doc.metal} - {doc.invoice_no}"

#         product_payload = {
#             "product": {
#                 "title": product_title,
#                 "status": "active"
#             }
#         }

#         res = requests.post(
#             f"https://{SHOP}/admin/api/{API_VERSION}/products.json",
#             json=product_payload,
#             headers=HEADERS
#         )

#         print("Product Create Response:", res.text)

#         data = res.json()

#         if "product" not in data:
#             frappe.throw(f"Shopify Product Error: {data}")

#         product_id = data["product"]["id"]

#     # ======================================
#     # 3️⃣ CREATE / UPDATE VARIANTS
#     # ======================================
#     for d in doc.sku_details:

#         # Check existing variant by SKU
#         vcheck = requests.get(
#             f"https://{SHOP}/admin/api/{API_VERSION}/variants.json?sku={d.sku}",
#             headers=HEADERS
#         ).json()

#         if vcheck.get("variants"):
#             variant = vcheck["variants"][0]
#             inventory_item_id = variant["inventory_item_id"]

#             # Update price
#             update_payload = {
#                 "variant": {
#                     "id": variant["id"],
#                     "price": d.selling_price
#                 }
#             }

#             requests.put(
#                 f"https://{SHOP}/admin/api/{API_VERSION}/variants/{variant['id']}.json",
#                 json=update_payload,
#                 headers=HEADERS
#             )

#         else:
#             # Create new variant
#             variant_payload = {
#                 "variant": {
#                     "product_id": product_id,
#                     "sku": d.sku,
#                     "price": d.selling_price,
#                     "inventory_management": "shopify"
#                 }
#             }

#             v = requests.post(
#                 f"https://{SHOP}/admin/api/{API_VERSION}/variants.json",
#                 json=variant_payload,
#                 headers=HEADERS
#             ).json()

#             if "variant" not in v:
#                 frappe.throw(f"Variant Error: {v}")

#             inventory_item_id = v["variant"]["inventory_item_id"]

#         # ======================================
#         # 4️⃣ INVENTORY UPDATE
#         # ======================================
#         inventory_payload = {
#             "location_id": LOCATION_ID,
#             "inventory_item_id": inventory_item_id,
#             "available": d.qty
#         }

#         inv = requests.post(
#             f"https://{SHOP}/admin/api/{API_VERSION}/inventory_levels/set.json",
#             json=inventory_payload,
#             headers=HEADERS
#         ).json()

#         if inv.get("errors"):
#             frappe.throw(f"Inventory Error: {inv}")

#     frappe.msgprint("🔥 Shopify Sync Complete (Pro Safe Mode)")
