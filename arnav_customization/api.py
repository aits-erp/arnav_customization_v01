# import frappe
# import base64
# from io import BytesIO

# try:
#     import qrcode
#     QR_AVAILABLE = True
# except ImportError:
#     QR_AVAILABLE = False


# @frappe.whitelist(allow_guest=True)
# def get_sku_details(warehouse=None):

#     if not warehouse:
#         frappe.throw("Warehouse is required")

#     site_url = frappe.utils.get_url()

#     # ✅ FIX: Proper filtering + no duplicate/mixed data
#     sku_details = frappe.db.sql("""
#         SELECT
#             sd.name as sku_name,
#             sd.sku,
#             sd.product,
#             i.item_name,
#             COALESCE(b.actual_qty, 0) as qty,
#             sd.selling_price,
#             sd.gross_weight,
#             sd.net_weight,
#             sd.huid,
#             sd.d_no,
#             sd.image
#         FROM `tabSKU Details` sd
#         LEFT JOIN `tabItem` i
#             ON i.name = sd.product
#         LEFT JOIN `tabBin` b
#             ON b.item_code = sd.product
#             AND b.warehouse = %(warehouse)s

#         -- ✅ IMPORTANT FILTER (only this warehouse data matters)
#         WHERE EXISTS (
#             SELECT 1 FROM `tabBin` b2
#             WHERE b2.item_code = sd.product
#             AND b2.warehouse = %(warehouse)s
#         )
#     """, {"warehouse": warehouse}, as_dict=True)

#     result = []

#     for item in sku_details:

#         # ✅ Image handling
#         image_path = item.get("image")
#         if image_path:
#             item["image_url"] = site_url + image_path
#             item["image_name"] = image_path.split("/")[-1]
#         else:
#             item["image_url"] = None
#             item["image_name"] = None

#         # ✅ QR Code
#         qr_data = item.get("sku") or item.get("sku_name")

#         if QR_AVAILABLE and qr_data:
#             try:
#                 qr = qrcode.make(qr_data)
#                 buffer = BytesIO()
#                 qr.save(buffer, format="PNG")

#                 qr_base64 = base64.b64encode(buffer.getvalue()).decode()
#                 item["qr_code"] = f"data:image/png;base64,{qr_base64}"
#             except Exception:
#                 item["qr_code"] = None
#         else:
#             item["qr_code"] = None

#         result.append(item)

#     return {
#         "status": "success",
#         "warehouse": warehouse,
#         "count": len(result),
#         "sku_details": result
#     }


# # ✅ Warehouse List (clean version)
# @frappe.whitelist(allow_guest=True)
# def get_location_master_list():

#     locations = frappe.get_all(
#         "Warehouse",
#         pluck="name"   # 🔥 cleaner + faster
#     )

#     return locations



import frappe
import base64
from io import BytesIO

# ✅ Safe import (prevents crash if qrcode not installed)
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

@frappe.whitelist(allow_guest=True)
def get_sku_details(warehouse=None):

    if not warehouse:
        frappe.throw("Warehouse is required")

    site_url = frappe.utils.get_url()

    # ✅ FIXED QUERY (important)
    # sku_details = frappe.db.sql("""
    #     SELECT
    #         sd.name as sku_name,
    #         sd.sku,
    #         sd.product,
    #         i.item_name,
    #         IFNULL(b.actual_qty, 0) as qty,
    #         sd.selling_price,
    #         sd.gross_weight,
    #         sd.net_weight,
    #         sd.huid,
    #         sd.d_no,
    #         sd.image
    #     FROM `tabSKU Details` sd
    #     LEFT JOIN `tabItem` i
    #         ON i.name = sd.product
    #     LEFT JOIN `tabBin` b
    #         ON b.item_code = sd.product
    #         AND b.warehouse = %s
    # """, (warehouse,), as_dict=True)
    
    # sku_details = frappe.db.sql("""
    #     SELECT
    #         MIN(sd.name) AS sku_name,
    #         MIN(sd.sku) AS sku,
    #         b.item_code AS product,
    #         i.item_name,
    #         b.actual_qty AS qty,
    #         MIN(sd.selling_price) AS selling_price,
    #         MIN(sd.gross_weight) AS gross_weight,
    #         MIN(sd.net_weight) AS net_weight,
    #         MIN(sd.huid) AS huid,
    #         MIN(sd.d_no) AS d_no,
    #         MIN(sd.image) AS image

    #     FROM tabBin b

    #     JOIN `tabItem` i
    #         ON i.name = b.item_code

    #     LEFT JOIN `tabSKU Details` sd
    #         ON sd.product = b.item_code

    #     WHERE b.warehouse = %(warehouse)s

    #     GROUP BY b.item_code
    # """, {"warehouse": warehouse}, as_dict=True)

	sku_details = frappe.db.sql("""
	    SELECT
	        sd.name AS sku_name,
	        sd.sku,
	        sd.product,
	        i.item_name,
	        b.actual_qty AS qty,
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
	        AND b.warehouse = %(warehouse)s
	
	    WHERE IFNULL(b.actual_qty, 0) > 0
	
	""", {"warehouse": warehouse}, as_dict=True)

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


@frappe.whitelist(allow_guest=True)
def get_location_master_list():

    locations = frappe.get_all(
        "Warehouse",
        fields=["name"]
    )

    # Return only list of names
    return [loc["name"] for loc in locations]

