import frappe

@frappe.whitelist(allow_guest=True)
def get_sku_master_with_details():

    # 🔹 Parent SKU Master fetch
    masters = frappe.get_all(
        "SKU Master",
        fields=[
            # "name",
            # "supplier_name",
            # "invoice_no",
            # "warehouse",
            "metal",
            # "hsn",
            # "note",
            # "date_of_invoice",
            # "date_of_received"
        ]
    )

    result = []

    for m in masters:

        # 🔹 Child Table fetch
        details = frappe.db.sql("""
            SELECT
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
            WHERE sd.parent = %s
        """, m.name, as_dict=True)

        m["sku_details"] = details
        result.append(m)

    return {
        "status": "success",
        "data": result
    }
