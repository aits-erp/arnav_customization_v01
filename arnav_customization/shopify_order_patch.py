import frappe

def smart_sku_mapper(doc, method=None):

    # Shopify orders ko detect karne ka optional check
    if not doc.get("shopify_order_id"):
        return

    for item in doc.items:

        # 🔹 Shopify integrations me SKU kabhi item_code me aata hai
        shopify_sku = item.get("sku") or item.get("item_code")

        if not shopify_sku:
            continue

        # 🔹 SKU Details table me search
        sku_detail = frappe.db.get_value(
            "SKU Details",
            {"sku": shopify_sku},
            ["sku", "product"],
            as_dict=True
        )

        if sku_detail:
            # ⭐ Sales Order Item me custom field set
            item.sku = sku_detail.sku

            # Optional: item_code auto map
            if sku_detail.product:
                item.item_code = sku_detail.product

    doc.save(ignore_permissions=True)
