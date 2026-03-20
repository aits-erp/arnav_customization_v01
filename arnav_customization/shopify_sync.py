import frappe
import requests

# ===============================
# CONFIG
# ===============================
SHOP = "jewel-box-arnav.myshopify.com"
TOKEN = "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"   # ⚠️ Replace
API_VERSION = "2024-01"
LOCATION_ID = 52386005145

HEADERS = {
    "X-Shopify-Access-Token": TOKEN,
    "Content-Type": "application/json"
}

# ===============================
# SAFE FLOAT
# ===============================
def f(val):
    try:
        return float(val or 0)
    except:
        return 0.0


# ===============================
# 🔒 SKU CHANGE VALIDATION
# ===============================
def validate_sku_change(doc):

    for d in doc.sku_details:

        if d.name and frappe.db.exists("SKU Details", d.name):
            old_sku = frappe.db.get_value("SKU Details", d.name, "sku")

            if old_sku and old_sku != d.sku:
                frappe.throw(f"❌ SKU change allowed nahi hai: {old_sku} → {d.sku}")


# ===============================
# CREATE PRODUCT (DRAFT)
# ===============================
def create_product(d):

    title = f"{d.product} - {d.sku}"

    description = f"""
    <b>Product:</b> {d.product}<br>
    <b>SKU:</b> {d.sku}<br>
    <b>Weight:</b> {d.gross_weight} g<br>
    <b>Price:</b> ₹{d.shopify_selling_rate}<br>

    """

    payload = {
        "product": {
            "title": title,
            "body_html": description,
            "status": "draft",   # ✅ CREATE = DRAFT
            "variants": [
                {
                    "sku": d.sku,
                    "price": f(d.shopify_selling_rate),
                    "weight": f(d.gross_weight),
                    "weight_unit": "g",
                    "inventory_management": "shopify"
                }
            ]
        }
    }

    res = requests.post(
        f"https://{SHOP}/admin/api/{API_VERSION}/products.json",
        json=payload,
        headers=HEADERS
    ).json()

    if "product" not in res:
        frappe.throw(f"Create Error: {res}")

    product = res["product"]
    variant = product["variants"][0]

    return product["id"], variant["id"], variant["inventory_item_id"]


# ===============================
# UPDATE PRODUCT (ACTIVE)
# ===============================
def update_product(d):

    title = f"{d.product} - {d.sku}"

    description = f"""
    <b>Product:</b> {d.product}<br>
    <b>SKU:</b> {d.sku}<br>
    <b>Weight:</b> {d.net_weight} g<br>
    <b>Price:</b> ₹{d.shopify_selling_rate}<br>
    <b>Cost:</b> ₹{d.cost_price}<br>
    """

    # ✅ UPDATE PRODUCT → ACTIVE (PUBLISH)
    requests.put(
        f"https://{SHOP}/admin/api/{API_VERSION}/products/{d.shopify_product_id}.json",
        json={
            "product": {
                "id": d.shopify_product_id,
                "title": title,
                "body_html": description,
                "status": "active"   # 🔥 UPDATE = ACTIVE
            }
        },
        headers=HEADERS
    )

    # ✅ UPDATE VARIANT (SKU LOCKED)
    res = requests.put(
        f"https://{SHOP}/admin/api/{API_VERSION}/variants/{d.shopify_variant_id}.json",
        json={
            "variant": {
                "id": d.shopify_variant_id,
                "price": f(d.shopify_selling_rate),
                "weight": f(d.gross_weight),
                "weight_unit": "g"
            }
        },
        headers=HEADERS
    ).json()

    if "errors" in res:
        frappe.throw(f"Variant Update Error: {res}")

    # ===============================
    # 🧹 DELETE OLD IMAGES
    # ===============================
    images = requests.get(
        f"https://{SHOP}/admin/api/{API_VERSION}/products/{d.shopify_product_id}/images.json",
        headers=HEADERS
    ).json()

    for img in images.get("images", []):
        requests.delete(
            f"https://{SHOP}/admin/api/{API_VERSION}/products/{d.shopify_product_id}/images/{img['id']}.json",
            headers=HEADERS
        )

    # ===============================
    # 🖼️ ADD NEW IMAGE
    # ===============================
    if getattr(d, "image_url", None):
        requests.post(
            f"https://{SHOP}/admin/api/{API_VERSION}/products/{d.shopify_product_id}/images.json",
            json={
                "image": {
                    "src": d.image_url
                }
            },
            headers=HEADERS
        )

    # ===============================
    # GET INVENTORY ITEM ID
    # ===============================
    v = requests.get(
        f"https://{SHOP}/admin/api/{API_VERSION}/variants/{d.shopify_variant_id}.json",
        headers=HEADERS
    ).json()

    return v["variant"]["inventory_item_id"]


# ===============================
# INVENTORY UPDATE
# ===============================
def update_inventory(inventory_item_id, qty):

    payload = {
        "location_id": LOCATION_ID,
        "inventory_item_id": inventory_item_id,
        "available": int(qty or 0)
    }

    res = requests.post(
        f"https://{SHOP}/admin/api/{API_VERSION}/inventory_levels/set.json",
        json=payload,
        headers=HEADERS
    ).json()

    if res.get("errors"):
        frappe.throw(f"Inventory Error: {res}")


# ===============================
# MAIN FUNCTION
# ===============================
def sync_each_sku_as_product(doc, method=None):

    validate_sku_change(doc)

    if not doc.sku_details:
        frappe.throw("No SKU Details found")

    for d in doc.sku_details:

        if not d.shopify_product_id:
            product_id, variant_id, inventory_item_id = create_product(d)

            d.shopify_product_id = product_id
            d.shopify_variant_id = variant_id
        else:
            inventory_item_id = update_product(d)

        update_inventory(inventory_item_id, d.qty)

    frappe.msgprint("🔥 Shopify Sync Complete (Draft → Active Flow)")


# ===============================
# BACKWARD COMPATIBILITY
# ===============================
def sync_to_shopify(doc, method=None):
    return sync_each_sku_as_product(doc, method)


# import frappe
# import requests

# # ===============================
# # SHOPIFY CONFIG
# # ===============================
# SHOP = "jewel-box-arnav.myshopify.com"
# TOKEN = "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"   # ⚠️ IMPORTANT: old token public ho gaya hai
# API_VERSION = "2024-01"
# LOCATION_ID = 52386005145

# HEADERS = {
#     "X-Shopify-Access-Token": TOKEN,
#     "Content-Type": "application/json"
# }

# # ===============================
# # SAFE FLOAT HELPER
# # ===============================
# def f(val):
#     try:
#         return float(val or 0)
#     except:
#         return 0.0


# # ===============================
# # FIND PRODUCT BY TITLE
# # ===============================
# def find_product_by_title(title):

#     res = requests.get(
#         f"https://{SHOP}/admin/api/{API_VERSION}/products.json?limit=250",
#         headers=HEADERS
#     ).json()

#     for p in res.get("products", []):
#         if p["title"].strip().lower() == title.strip().lower():
#             return p["id"]

#     return None


# # ===============================
# # GET PRODUCT VARIANTS
# # ===============================
# def get_product_variants(product_id):

#     res = requests.get(
#         f"https://{SHOP}/admin/api/{API_VERSION}/products/{product_id}/variants.json",
#         headers=HEADERS
#     ).json()

#     return res.get("variants", [])


# # ===============================
# # MAIN SYNC FUNCTION
# # ===============================
# def sync_to_shopify(doc, method=None):

#     if not doc.sku_details:
#         frappe.throw("No SKU Details found")

#     product_title = doc.sku_details[0].product.strip()

#     # ====================================================
#     # 1️⃣ FIND OR CREATE PRODUCT (DRAFT MODE)
#     # ====================================================
#     product_id = doc.get("shopify_product_id")

#     if not product_id:
#         product_id = find_product_by_title(product_title)

#     if not product_id:

#         # ⭐ FIRST VARIANT PAYLOAD (IMPORTANT - NO DEFAULT TITLE)
#         first = doc.sku_details[0]

#         product_payload = {
#             "product": {
#                 "title": product_title,
#                 "status": "draft",
#                 "options": [{"name": "SKU"}],
#                 "variants": [
#                     {
#                         "sku": first.sku,
#                         "price": f(first.shopify_selling_rate),
#                         "compare_at_price": f(first.cost_price),
#                         "weight": f(first.net_weight),
#                         "weight_unit": "g",
#                         "inventory_management": "shopify",
#                         "option1": first.sku
#                     }
#                 ]
#             }
#         }

#         res = requests.post(
#             f"https://{SHOP}/admin/api/{API_VERSION}/products.json",
#             json=product_payload,
#             headers=HEADERS
#         ).json()

#         if "product" not in res:
#             frappe.throw(f"Shopify Product Error: {res}")

#         product_id = res["product"]["id"]
#         doc.db_set("shopify_product_id", product_id)

#     # ====================================================
#     # 2️⃣ FORCE PRODUCT TO DRAFT (NO AUTO PUBLISH)
#     # ====================================================
#     requests.put(
#         f"https://{SHOP}/admin/api/{API_VERSION}/products/{product_id}.json",
#         json={"product": {"id": product_id, "status": "draft"}},
#         headers=HEADERS
#     )

#     # ====================================================
#     # 3️⃣ GET EXISTING VARIANTS
#     # ====================================================
#     existing_variants = get_product_variants(product_id)

#     # ====================================================
#     # 4️⃣ MULTI SKU LOOP
#     # ====================================================
#     for d in doc.sku_details:

#         existing_variant = None

#         for v in existing_variants:
#             if v.get("sku") == d.sku:
#                 existing_variant = v
#                 break

#         # ------------------------------------------------
#         # UPDATE EXISTING VARIANT
#         # ------------------------------------------------
#         if existing_variant:

#             inventory_item_id = existing_variant["inventory_item_id"]

#             update_payload = {
#                 "variant": {
#                     "id": existing_variant["id"],
#                     "price": f(d.shopify_selling_rate),
#                     "compare_at_price": f(d.cost_price),
#                     "weight": f(d.net_weight),
#                     "weight_unit": "g"
#                 }
#             }

#             r = requests.put(
#                 f"https://{SHOP}/admin/api/{API_VERSION}/variants/{existing_variant['id']}.json",
#                 json=update_payload,
#                 headers=HEADERS
#             ).json()

#             if "errors" in r:
#                 frappe.throw(f"Variant Update Error: {r}")

#         # ------------------------------------------------
#         # CREATE NEW VARIANT
#         # ------------------------------------------------
#         else:

#             variant_payload = {
#                 "variant": {
#                     "sku": d.sku,
#                     "price": f(d.shopify_selling_rate),
#                     "compare_at_price": f(d.cost_price),
#                     "weight": f(d.net_weight),
#                     "weight_unit": "g",
#                     "inventory_management": "shopify",
#                     "option1": d.sku
#                 }
#             }

#             v = requests.post(
#                 f"https://{SHOP}/admin/api/{API_VERSION}/products/{product_id}/variants.json",
#                 json=variant_payload,
#                 headers=HEADERS
#             ).json()

#             if "variant" not in v:
#                 frappe.throw(f"Variant Create Error: {v}")

#             inventory_item_id = v["variant"]["inventory_item_id"]

#         # ------------------------------------------------
#         # INVENTORY UPDATE
#         # ------------------------------------------------
#         inventory_payload = {
#             "location_id": LOCATION_ID,
#             "inventory_item_id": inventory_item_id,
#             "available": int(d.qty or 0)
#         }

#         inv = requests.post(
#             f"https://{SHOP}/admin/api/{API_VERSION}/inventory_levels/set.json",
#             json=inventory_payload,
#             headers=HEADERS
#         ).json()

#         if inv.get("errors"):
#             frappe.throw(f"Inventory Error: {inv}")

#     frappe.msgprint("🔥 Shopify Draft Sync Success (PRO MODE)")
