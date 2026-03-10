import frappe

def get_sku_data(sku):
    if not sku:
        return None

    return frappe.db.get_value(
        "SKU",
        sku,
        [
            "product",
            "batch_no",
            "warehouse",
            "gross_weight",
            "net_weight",
            "qty",
            "cost_price",
            "selling_price",
            "image_url",
            "sku_master",
            "metal",
            "supplier",
            "hsn",
            "barcode",
            "valuation_rate",
            "old_sku_ref"
        ],
        as_dict=True
    )