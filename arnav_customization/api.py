import frappe

# 🔹 SKU Details List Endpoint (Child Table)
@frappe.whitelist(allow_guest=True)
def get_sku_details():

    data = frappe.db.sql("""
        SELECT 
            sd.name,
            sd.sku,
            sd.product,
            i.item_name,
            sd.qty,
            sd.selling_price,
            sd.gross_weight,
            sd.net_weight,
            sd.image
        FROM `tabSKU Details` sd
        LEFT JOIN `tabItem` i
        ON i.name = sd.product
    """, as_dict=True)

    return {
        "status": "success",
        "data": data
    }
