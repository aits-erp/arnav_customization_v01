import frappe

@frappe.whitelist(allow_guest=True)
def get_sku_master_with_details():

    masters = frappe.get_all(
        "SKU Master",
        fields=[
            "name",        # ⭐ backend ke liye required
            "warehouse",
            "metal"
        ]
    )

    result = []

    for m in masters:

        # 🔹 Fetch Warehouse Address
        address = frappe.db.sql("""
            SELECT
                a.address_line1,
                a.city,
                a.state,
                a.pincode,
                a.country
            FROM `tabAddress` a
            LEFT JOIN `tabDynamic Link` dl
                ON dl.parent = a.name
            WHERE dl.link_doctype = 'Warehouse'
            AND dl.link_name = %s
            LIMIT 1
        """, (m["warehouse"],), as_dict=True)

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
        """, (m["name"],), as_dict=True)

        # ⭐ Attach data
        m["warehouse_address"] = address[0] if address else {}
        m["sku_details"] = details

        # ⭐ REMOVE name from response
        m.pop("name", None)

        result.append(m)

    return {
        "status": "success",
        "data": result
    }



# import frappe

# @frappe.whitelist(allow_guest=True)
# def get_sku_master_with_details():

#     # 🔹 Parent SKU Master fetch
#     masters = frappe.get_all(
#         "SKU Master",
#         fields=[
#             # "name",
#             # "supplier_name",
#             # "invoice_no",
#             "warehouse",
#             "metal",
#             # "hsn",
#             # "note",
#             # "date_of_invoice",
#             # "date_of_received"
#         ]
#     )

#     result = []

#     for m in masters:

#         # 🔹 Child Table fetch
#         details = frappe.db.sql("""
#             SELECT
#                 sd.sku,
#                 sd.product,
#                 i.item_name,
#                 sd.qty,
#                 sd.selling_price,
#                 sd.gross_weight,
#                 sd.net_weight,
#                 sd.image
#             FROM `tabSKU Details` sd
#             LEFT JOIN `tabItem` i
#             ON i.name = sd.product
#             WHERE sd.parent = %s
#         """, m.name, as_dict=True)

#         m["sku_details"] = details
#         result.append(m)

#     return {
#         "status": "success",
#         "data": result
#     }
