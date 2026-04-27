import frappe
import base64
from io import BytesIO

# ✅ Safe import (prevents crash if qrcode not installed)
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
def rename_and_update_image(doc, method):

    # ✅ Image field
    image_path = doc.image
    if not image_path:
        return

    # ✅ Get file document
    file_doc = frappe.db.get_value(
        "File",
        {"file_url": image_path},
        ["name", "file_name", "file_url", "is_private"],
        as_dict=True
    )

    if not file_doc:
        return

    # ✅ SKU code
    sku_code = doc.sku or doc.name
    if not sku_code:
        return

    # ✅ Extension
    ext = os.path.splitext(file_doc.file_name)[1]

    # ✅ New file name
    new_file_name = f"{sku_code}{ext}"

    # Avoid duplicate conflict
    if frappe.db.exists("File", {"file_name": new_file_name}):
        new_file_name = f"{sku_code}_{frappe.generate_hash(length=4)}{ext}"

    # ✅ Get full file path
    old_file = frappe.get_doc("File", file_doc.name)
    file_content = old_file.get_content()

    # ✅ Save new file
    new_file = frappe.get_doc({
        "doctype": "File",
        "file_name": new_file_name,
        "attached_to_doctype": "SKU Details",
        "attached_to_name": doc.name,
        "is_private": file_doc.is_private,
        "content": file_content
    })
    new_file.insert(ignore_permissions=True)

    # ✅ Update SKU image field with new URL
    doc.db_set("image", new_file.file_url)

    # ✅ Delete old file (optional but recommended)
    try:
        frappe.delete_doc("File", file_doc.name)
    except Exception:
        pass

    frappe.db.commit()

@frappe.whitelist(allow_guest=True)
def get_sku_details(warehouse=None):

    if not warehouse:
        frappe.throw("Warehouse is required")

    site_url = frappe.utils.get_url()

    # ✅ FIXED QUERY (important)
    sku_details = frappe.db.sql("""
        SELECT
            sd.name as sku_name,
            sd.sku,
            sd.product,
            i.item_name,
            IFNULL(b.actual_qty, 0) as qty,
            sd.selling_price,
            sd.gross_weight,
            sd.net_weight,
            sd.huid,
            sd.d_no,
            sd.image
        FROM `tabSKU Details` sd
        LEFT JOIN `tabItem` i
            ON i.name = sd.product
        LEFT JOIN `tabBin` b
            ON b.item_code = sd.product
            AND b.warehouse = %s
    """, (warehouse,), as_dict=True)

    for item in sku_details:

        # ✅ Image URL + Name
        image_path = item.get("image")
        if image_path:
            item["image_url"] = site_url + image_path
            item["image_name"] = image_path.split("/")[-1]
        else:
            item["image_url"] = None
            item["image_name"] = None

        # ✅ QR Code (safe)
        qr_data = item.get("sku") or item.get("sku_name")

        if QR_AVAILABLE and qr_data:
            try:
                qr = qrcode.make(qr_data)
                buffer = BytesIO()
                qr.save(buffer, format="PNG")

                qr_base64 = base64.b64encode(buffer.getvalue()).decode()
                item["qr_code"] = f"data:image/png;base64,{qr_base64}"
            except Exception:
                item["qr_code"] = None
        else:
            item["qr_code"] = None

    return {
        "sku_details": sku_details
    }


# import frappe

# @frappe.whitelist(allow_guest=True)
# def get_location_master_list():

#     locations = frappe.get_all(
#         "Warehouse",
#         fields=["name"]
#     )

#     # Return only list of names
#     return [loc["name"] for loc in locations]



# @frappe.whitelist(allow_guest=True)
# def get_sku_details(warehouse=None):

#     if not warehouse:
#         frappe.throw("Warehouse is required")

#     sku_details = frappe.db.sql("""
#         SELECT
#             sd.sku,
#             sd.product,
#             i.item_name,
#             IFNULL(b.actual_qty,0) as qty,
#             sd.selling_price,
#             sd.gross_weight,
#             sd.net_weight,
# 			sd.huid,
# 			sd.d_no,
#             sd.image
#         FROM `tabSKU Details` sd
#         LEFT JOIN `tabItem` i
#             ON i.name = sd.product
#         LEFT JOIN `tabBin` b
#             ON b.item_code = sd.product
#         WHERE b.warehouse = %s
#     """, (warehouse,), as_dict=True)

#     return {
#         "sku_details": sku_details
#     }

# @frappe.whitelist(allow_guest=True)
# def get_sku_details():

#     details = frappe.db.sql("""
#         SELECT
#             sd.sku,
#             sd.product,
#             i.item_name,
#             sd.qty,
#             sd.selling_price,
#             sd.gross_weight,
#             sd.net_weight,
#             sd.image
#         FROM `tabSKU Details` sd
#         LEFT JOIN `tabItem` i
#             ON i.name = sd.product
#     """, as_dict=True)

#     return {
#         "sku_details": details
#     }



# import frappe

# @frappe.whitelist(allow_guest=True)
# def get_sku_master_with_details():

#     masters = frappe.get_all(
#         "SKU Master",
#         fields=[
#             "name",        # ⭐ backend ke liye required
#             "warehouse",
#             "metal"
#         ]
#     )

#     result = []

#     for m in masters:

#         # 🔹 Fetch Warehouse Address
#         address = frappe.db.sql("""
#             SELECT
#                 a.address_line1,
#                 a.city,
#                 a.state,
#                 a.pincode,
#                 a.country
#             FROM `tabAddress` a
#             LEFT JOIN `tabDynamic Link` dl
#                 ON dl.parent = a.name
#             WHERE dl.link_doctype = 'Warehouse'
#             AND dl.link_name = %s
#             LIMIT 1
#         """, (m["warehouse"],), as_dict=True)

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
#                 ON i.name = sd.product
#             WHERE sd.parent = %s
#         """, (m["name"],), as_dict=True)

#         # ⭐ Attach data
#         m["warehouse_address"] = address[0] if address else {}
#         m["sku_details"] = details

#         # ⭐ REMOVE name from response
#         m.pop("name", None)

#         result.append(m)

#     return {
#         "status": "success",
#         "data": result
#     }



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
