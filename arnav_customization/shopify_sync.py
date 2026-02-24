import frappe
import requests

# ===============================
# SHOPIFY CONFIG
# ===============================
SHOP = "jewel-box-arnav.myshopify.com"
TOKEN = "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"   # ⚠️ IMPORTANT: old token public ho gaya hai
API_VERSION = "2024-01"
LOCATION_ID = 52386005145

HEADERS = {
    "X-Shopify-Access-Token": TOKEN,
    "Content-Type": "application/json"
}

# ===============================
# SAFE FLOAT HELPER
# ===============================
def f(val):
    try:
        return float(val or 0)
    except:
        return 0.0


# ===============================
# FIND PRODUCT BY TITLE
# ===============================
def find_product_by_title(title):

    res = requests.get(
        f"https://{SHOP}/admin/api/{API_VERSION}/products.json?limit=250",
        headers=HEADERS
    ).json()

    for p in res.get("products", []):
        if p["title"].strip().lower() == title.strip().lower():
            return p["id"]

    return None


# ===============================
# GET PRODUCT VARIANTS
# ===============================
def get_product_variants(product_id):

    res = requests.get(
        f"https://{SHOP}/admin/api/{API_VERSION}/products/{product_id}/variants.json",
        headers=HEADERS
    ).json()

    return res.get("variants", [])


# ===============================
# MAIN SYNC FUNCTION
# ===============================
def sync_to_shopify(doc, method=None):

    if not doc.sku_details:
        frappe.throw("No SKU Details found")

    product_title = doc.sku_details[0].product

    # ====================================================
    # 1️⃣ FIND OR CREATE PRODUCT
    # ====================================================
    product_id = doc.get("shopify_product_id")

    if not product_id:
        product_id = find_product_by_title(product_title)

    if not product_id:

        product_payload = {
            "product": {
                "title": product_title,
                "status": "active",
                "options": [{"name": "SKU"}]
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
        doc.db_set("shopify_product_id", product_id)

    # UNARCHIVE PRODUCT
    requests.put(
        f"https://{SHOP}/admin/api/{API_VERSION}/products/{product_id}.json",
        json={"product": {"id": product_id, "status": "active"}},
        headers=HEADERS
    )

    # ====================================================
    # 2️⃣ GET EXISTING VARIANTS
    # ====================================================
    existing_variants = get_product_variants(product_id)

    # ====================================================
    # 3️⃣ LOOP MULTI SKU
    # ====================================================
    for d in doc.sku_details:

        existing_variant = None

        for v in existing_variants:
            if v.get("sku") == d.sku:
                existing_variant = v
                break

        # ------------------------------------------------
        # UPDATE EXISTING VARIANT
        # ------------------------------------------------
        if existing_variant:

            inventory_item_id = existing_variant["inventory_item_id"]

            update_payload = {
                "variant": {
                    "id": existing_variant["id"],
                    "sku": d.sku,
                    "price": f(d.selling_price),
                    "compare_at_price": f(d.cost_price),
                    "weight": f(d.net_weight),
                    "weight_unit": "g",
                    "inventory_management": "shopify",
                    "option1": d.sku
                }
            }

            r = requests.put(
                f"https://{SHOP}/admin/api/{API_VERSION}/variants/{existing_variant['id']}.json",
                json=update_payload,
                headers=HEADERS
            ).json()

            if "errors" in r:
                frappe.throw(f"Variant Update Error: {r}")

        # ------------------------------------------------
        # CREATE NEW VARIANT
        # ------------------------------------------------
        else:

            variant_payload = {
                "variant": {
                    "sku": d.sku,
                    "price": f(d.selling_price),
                    "compare_at_price": f(d.cost_price),
                    "weight": f(d.net_weight),
                    "weight_unit": "g",
                    "inventory_management": "shopify",
                    "option1": d.sku
                }
            }

            v = requests.post(
                f"https://{SHOP}/admin/api/{API_VERSION}/products/{product_id}/variants.json",
                json=variant_payload,
                headers=HEADERS
            ).json()

            if "variant" not in v:
                frappe.throw(f"Variant Create Error: {v}")

            inventory_item_id = v["variant"]["inventory_item_id"]

        # ------------------------------------------------
        # INVENTORY UPDATE
        # ------------------------------------------------
        inventory_payload = {
            "location_id": LOCATION_ID,
            "inventory_item_id": inventory_item_id,
            "available": int(d.qty or 0)
        }

        inv = requests.post(
            f"https://{SHOP}/admin/api/{API_VERSION}/inventory_levels/set.json",
            json=inventory_payload,
            headers=HEADERS
        ).json()

        if inv.get("errors"):
            frappe.throw(f"Inventory Error: {inv}")

    # ====================================================
    # ⭐ SEO PRICE FIX (FIRST VARIANT UPDATE)
    # ====================================================
    variants = get_product_variants(product_id)

    if variants:
        first_price = f(doc.sku_details[0].selling_price)

        requests.put(
            f"https://{SHOP}/admin/api/{API_VERSION}/variants/{variants[0]['id']}.json",
            json={
                "variant": {
                    "id": variants[0]["id"],
                    "price": first_price
                }
            },
            headers=HEADERS
        )

    frappe.msgprint("🔥 Shopify FULL Sync Success (SEO ₹0.00 FIXED)")






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
