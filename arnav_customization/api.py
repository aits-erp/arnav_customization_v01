import frappe

@frappe.whitelist(allow_guest=True)
def create_sku_via_api(product=None, sku=None):

    # ⭐ Only READ DATA
    data = frappe.db.sql("""
        SELECT 
            i.item_code,
            i.item_name,
            IFNULL(b.batch_id, '') AS sku
        FROM `tabItem` i
        LEFT JOIN `tabBatch` b
            ON b.item = i.name
        WHERE (%(product)s IS NULL OR i.item_code = %(product)s)
          AND (%(sku)s IS NULL OR b.batch_id = %(sku)s)
    """, {"product": product, "sku": sku}, as_dict=True)

    return {
        "status": "success",
        "data": data
    }
