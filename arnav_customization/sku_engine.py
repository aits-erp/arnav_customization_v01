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

        # ⭐ Child table me batch assign
        row.batch_no = row.sku

        # ⭐ Item update
        item = frappe.get_doc("Item", row.product)
        item.barcode = row.sku
        item.custom_is_shopify_ready = 1
        item.save(ignore_permissions=True)

        # ⭐ Shopify Update (FIXED)
        try:
            from ecommerce_integrations.shopify.utils import upload_item_to_shopify

            upload_item_to_shopify(item.name)

            frappe.msgprint(f"Shopify Updated SKU: {row.sku}")

        except Exception as e:
            frappe.log_error(str(e), "Shopify Auto Sync Error")
