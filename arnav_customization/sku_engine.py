import frappe

def create_sku_from_custom_doc(doc, method=None):

    # Child table name change karo agar alag hai
    for row in doc.sku_details:

        if not row.sku:
            continue

        # ⭐ Batch = SKU create
        if not frappe.db.exists("Batch", {"batch_id": row.sku}):

            batch = frappe.new_doc("Batch")
            batch.batch_id = row.sku
            batch.item = row.product
            batch.insert(ignore_permissions=True)

        # ⭐ Item barcode update
        item = frappe.get_doc("Item", row.product)
        item.barcode = row.sku
        item.save(ignore_permissions=True)

        # ⭐ Shopify auto sync
        try:
            from erpnext_shopify.shopify_api import ShopifyAPI
            shopify = ShopifyAPI()
            shopify.sync_products(item)
        except Exception as e:
            frappe.log_error(str(e), "Shopify Sync Error")
