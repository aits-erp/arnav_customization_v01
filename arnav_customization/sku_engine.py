import frappe

def create_sku_from_custom_doc(doc, method=None):

    for row in doc.sku_details:

        if not row.sku:
            continue

        # ⭐ Batch Create = SKU
        if not frappe.db.exists("Batch", {"batch_id": row.sku}):

            batch = frappe.new_doc("Batch")
            batch.batch_id = row.sku
            batch.item = row.product
            batch.insert(ignore_permissions=True)

        # ⭐ Item update
        item = frappe.get_doc("Item", row.product)
        item.barcode = row.sku

        # ⭐ Custom flag laga do (important)
        item.custom_is_shopify_ready = 1

        item.save(ignore_permissions=True)

        # ⭐ ONLY THIS ITEM SHOPIFY PUSH
        try:
            from erpnext_shopify.shopify_api import ShopifyAPI

            shopify = ShopifyAPI()
            shopify.sync_products(item)

        except Exception as e:
            frappe.log_error(str(e), "Shopify Auto Sync Error")
