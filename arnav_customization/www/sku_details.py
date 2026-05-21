import frappe

def get_context(context):

    sku = frappe.form_dict.sku

    if not sku:
        context.message = "SKU not found"
        return context

    data = frappe.db.sql("""
        SELECT
            sd.sku,
            i.item_name,
            sd.selling_price,
            sd.image
        FROM `tabSKU Details` sd
        LEFT JOIN `tabItem` i ON i.name = sd.product
        WHERE sd.sku = %s
    """, (sku,), as_dict=True)

    if data:
        item = data[0]
        context.item = item
        context.image_url = frappe.utils.get_url() + item.get("image", "")
    else:
        context.message = "No data found"

    return context
