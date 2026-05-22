import frappe
import base64
from io import BytesIO
from urllib.parse import quote
from urllib.parse import unquote

# Safe import prevents crash if qrcode is not installed
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False


# =========================================================
# Breakup Value Cleaner
# =========================================================
def _is_empty_breakup_value(value):
    if value is None:
        return True

    if isinstance(value, str):
        value = value.strip()

        if value == "":
            return True

        if value.lower() in ["none", "null"]:
            return True

        if frappe.utils.flt(value) == 0:
            return True

        return False

    return frappe.utils.flt(value) == 0


def _clean_breakup_row(row):
    # Keep attribute_type and attribute_value always.
    # Only hide empty/zero weight, price, and unit.
    for field in ["weight", "price", "unit"]:
        if _is_empty_breakup_value(row.get(field)):
            row.pop(field, None)

    return row


# =========================================================
# Reusable SKU Data Builder
# =========================================================
def _get_sku_details_data(warehouse=None, sku=None):

    site_url = frappe.utils.get_url()

    # =========================================================
    # Dynamic Conditions
    # =========================================================
    conditions = []
    filters = {}

    if warehouse:
        conditions.append("s.warehouse = %(warehouse)s")
        filters["warehouse"] = warehouse

    if sku:
        conditions.append("s.name = %(sku)s")
        filters["sku"] = sku

    where_clause = " AND ".join(conditions)

    # =========================================================
    # Main SKU Query
    # =========================================================
    sku_details = frappe.db.sql(f"""
        SELECT
            s.name AS sku_name,
            s.name AS sku,
            s.product,
            s.sku_master,
            s.breakup_ref,
            s.old_sku_ref,
            s.image_url,
            1 AS qty,
            s.selling_price,
            s.gross_weight,
            s.net_weight,
            s.huid,
            s.d_no

        FROM `tabSKU` s

        WHERE {where_clause}
    """, filters, as_dict=True)

    # =========================================================
    # Process Each SKU
    # =========================================================
    for item in sku_details:

        # =====================================================
        # Public QR URL
        # =====================================================
        qr_url = (
            f"{site_url}/sku_qr"
            f"?sku={quote(item.get('sku') or '')}"
        )

        item["qr_url"] = qr_url

        # =====================================================
        # Common Attribute Rows
        # =====================================================
        common_rows = frappe.get_all(
            "SKU Breakup",
            filters={
                "sku_master": item.get("sku_master"),
                "attribute_type": ["in", [
                    "PURITY",
                    "PRODUCT_TYPE",
                    "DESIGN",
                    "TARGET",
                    "VISUAL",
                    "COLLECTION"
                ]]
            },
            fields=[
                "attribute_type",
                "attribute_value",
                "weight",
                "price",
                "unit"
            ],
            order_by="creation asc"
        )

        # =====================================================
        # Breakup Specific Rows
        # =====================================================
        specific_rows = frappe.get_all(
            "SKU Breakup",
            filters={
                "sku_master": item.get("sku_master"),
                "breakup_ref": item.get("breakup_ref")
            },
            fields=[
                "attribute_type",
                "attribute_value",
                "weight",
                "price",
                "unit"
            ],
            order_by="creation asc"
        )

        # =====================================================
        # Merge Both
        # =====================================================
        breakup_rows = common_rows + specific_rows

        # =====================================================
        # Unit Short Forms
        # =====================================================
        UNIT_MAP = {
            "Carat": "cts",
            "Gram": "gm"
        }

        cleaned_breakup_rows = []

        for row in breakup_rows:
            if row.get("unit"):
                row["unit"] = UNIT_MAP.get(row.get("unit"), row.get("unit"))

            row = _clean_breakup_row(row)
            cleaned_breakup_rows.append(row)

        item["breakup"] = cleaned_breakup_rows or []

        # =====================================================
        # Image URL + Name
        # =====================================================
        image_path = item.get("image_url")

        if image_path:

            # Convert relative path to full URL
            if image_path.startswith("/"):
                full_image_url = site_url + image_path
            else:
                full_image_url = image_path

            item["image_url"] = full_image_url
            item["image_name"] = image_path.split("/")[-1]

        else:
            item["image_url"] = None
            item["image_name"] = None

        # =====================================================
        # QR Code Generation
        # =====================================================
        item["qr_code"] = None

        if QR_AVAILABLE and qr_url:

            try:
                qr = qrcode.make(qr_url)

                buffer = BytesIO()
                qr.save(buffer, format="PNG")

                qr_base64 = base64.b64encode(
                    buffer.getvalue()
                ).decode()

                item["qr_code"] = (
                    f"data:image/png;base64,{qr_base64}"
                )

            except Exception:
                frappe.log_error(
                    title="QR Code Generation Failed",
                    message=frappe.get_traceback()
                )

                item["qr_code"] = None

    return sku_details


# =========================================================
# Public API
# =========================================================
@frappe.whitelist(allow_guest=True)
def get_sku_details(warehouse=None, sku=None):

    # =========================================================
    # Validation
    # =========================================================
    if warehouse:
        warehouse = unquote(warehouse)

    if not warehouse and not sku:
        frappe.throw("Warehouse or SKU is required")

    sku_details = _get_sku_details_data(
        warehouse=warehouse,
        sku=sku
    )

    return {
        "sku_details": sku_details
    }


# =========================================================
# Warehouse List API
# =========================================================
@frappe.whitelist(allow_guest=True)
def get_location_master_list():

    locations = frappe.get_all(
        "Warehouse",
        filters={
            "custom_include_in_rfid": 1
        },
        fields=["name"],
        order_by="name asc"
    )

    return [
        {
            "warehouse_name": loc["name"],
            "warehouse_encoded": quote(loc["name"])
        }
        for loc in locations
    ]


# =========================================================
# Debug QR Library Check
# =========================================================
@frappe.whitelist(allow_guest=True)
def debug_qr_install():

    result = {}

    # =====================================================
    # Check qrcode
    # =====================================================
    try:
        import qrcode

        result["qrcode_import"] = "SUCCESS"
        result["qrcode_version"] = getattr(qrcode, "__version__", "UNKNOWN")

    except Exception as e:
        result["qrcode_import"] = str(e)

    # =====================================================
    # Check PIL
    # =====================================================
    try:
        from PIL import Image

        result["pillow_import"] = "SUCCESS"

    except Exception as e:
        result["pillow_import"] = str(e)

    # =====================================================
    # Try QR Generation
    # =====================================================
    try:
        import qrcode
        from io import BytesIO

        qr = qrcode.make("TEST QR")

        buffer = BytesIO()

        qr.save(buffer, format="PNG")

        result["qr_generation"] = "SUCCESS"

    except Exception as e:
        result["qr_generation"] = str(e)

    return result


# # import frappe
# # import base64
# # from io import BytesIO

# # try:
# #     import qrcode
# #     QR_AVAILABLE = True
# # except ImportError:
# #     QR_AVAILABLE = False

# # @frappe.whitelist(allow_guest=True)
# # def get_sku_details(warehouse=None):

# #     if not warehouse:
# #         frappe.throw("Warehouse is required")

# #     site_url = frappe.utils.get_url()

# #     # ✅ FIX: Proper filtering + no duplicate/mixed data
# #     sku_details = frappe.db.sql("""
# #         SELECT
# #             sd.name as sku_name,
# #             sd.sku,
# #             sd.product,
# #             i.item_name,
# #             COALESCE(b.actual_qty, 0) as qty,
# #             sd.selling_price,
# #             sd.gross_weight,
# #             sd.net_weight,
# #             sd.huid,
# #             sd.d_no,
# #             sd.image
# #         FROM `tabSKU Details` sd
# #         LEFT JOIN `tabItem` i
# #             ON i.name = sd.product
# #         LEFT JOIN `tabBin` b
# #             ON b.item_code = sd.product
# #             AND b.warehouse = %(warehouse)s

# #         -- ✅ IMPORTANT FILTER (only this warehouse data matters)
# #         WHERE EXISTS (
# #             SELECT 1 FROM `tabBin` b2
# #             WHERE b2.item_code = sd.product
# #             AND b2.warehouse = %(warehouse)s
# #         )
# #     """, {"warehouse": warehouse}, as_dict=True)

# #     result = []

# #     for item in sku_details:

# #         # ✅ Image handling
# #         image_path = item.get("image")
# #         if image_path:
# #             item["image_url"] = site_url + image_path
# #             item["image_name"] = image_path.split("/")[-1]
# #         else:
# #             item["image_url"] = None
# #             item["image_name"] = None

# #         # ✅ QR Code
# #         qr_data = item.get("sku") or item.get("sku_name")

# #         if QR_AVAILABLE and qr_data:
# #             try:
# #                 qr = qrcode.make(qr_data)
# #                 buffer = BytesIO()
# #                 qr.save(buffer, format="PNG")

# #                 qr_base64 = base64.b64encode(buffer.getvalue()).decode()
# #                 item["qr_code"] = f"data:image/png;base64,{qr_base64}"
# #             except Exception:
# #                 item["qr_code"] = None
# #         else:
# #             item["qr_code"] = None

# #         result.append(item)

# #     return {
# #         "status": "success",
# #         "warehouse": warehouse,
# #         "count": len(result),
# #         "sku_details": result
# #     }

# # # ✅ Warehouse List (clean version)
# # @frappe.whitelist(allow_guest=True)
# # def get_location_master_list():

# #     locations = frappe.get_all(
# #         "Warehouse",
# #         pluck="name"   # 🔥 cleaner + faster
# #     )

# #     return locations

# # import frappe
# # import base64
# # from io import BytesIO

# # # ✅ Safe import (prevents crash if qrcode not installed)
# # try:
# #     import qrcode
# #     QR_AVAILABLE = True
# # except ImportError:
# #     QR_AVAILABLE = False

# # @frappe.whitelist(allow_guest=True)
# # def get_sku_details(warehouse=None):

# #     if not warehouse:
# #         frappe.throw("Warehouse is required")

# #     site_url = frappe.utils.get_url()

# #     # # ✅ FIXED QUERY (important)
# #     # sku_details = frappe.db.sql("""
# #     #     SELECT
# #     #         sd.name as sku_name,
# #     #         sd.sku,
# #     #         sd.product,
# #     #         i.item_name,
# #     #         IFNULL(b.actual_qty, 0) as qty,
# #     #         sd.selling_price,
# #     #         sd.gross_weight,
# #     #         sd.net_weight,
# #     #         sd.huid,
# #     #         sd.d_no,
# #     #         sd.image
# #     #     FROM `tabSKU Details` sd
# #     #     LEFT JOIN `tabItem` i
# #     #         ON i.name = sd.product
# #     #     LEFT JOIN `tabBin` b
# #     #         ON b.item_code = sd.product
# #     #         AND b.warehouse = %s
# #     # """, (warehouse,), as_dict=True)
    
# #     # sku_details = frappe.db.sql("""
# #     #     SELECT
# #     #         MIN(sd.name) AS sku_name,
# #     #         MIN(sd.sku) AS sku,
# #     #         b.item_code AS product,
# #     #         i.item_name,
# #     #         b.actual_qty AS qty,
# #     #         MIN(sd.selling_price) AS selling_price,
# #     #         MIN(sd.gross_weight) AS gross_weight,
# #     #         MIN(sd.net_weight) AS net_weight,
# #     #         MIN(sd.huid) AS huid,
# #     #         MIN(sd.d_no) AS d_no,
# #     #         MIN(sd.image) AS image

# #     #     FROM tabBin b

# #     #     JOIN `tabItem` i
# #     #         ON i.name = b.item_code

# #     #     LEFT JOIN `tabSKU Details` sd
# #     #         ON sd.product = b.item_code

# #     #     WHERE b.warehouse = %(warehouse)s

# #     #     GROUP BY b.item_code
# #     # """, {"warehouse": warehouse}, as_dict=True)

# #     # sku_details = frappe.db.sql("""
# # 	#     SELECT
# # 	#         sd.name AS sku_name,
# # 	#         sd.sku,
# # 	#         sd.product,
# # 	#         i.item_name,
# # 	#         IFNULL(b.actual_qty, 0) AS qty,
# # 	#         sd.selling_price,
# # 	#         sd.gross_weight,
# # 	#         sd.net_weight,
# # 	#         sd.huid,
# # 	#         sd.d_no,
# # 	#         sd.image
	
# # 	#     FROM `tabSKU Details` sd
	
# # 	#     INNER JOIN `tabItem` i
# # 	#         ON i.name = sd.product
	
# # 	#     LEFT JOIN `tabBin` b
# # 	#         ON b.item_code = sd.product
# # 	#         AND b.warehouse = %(warehouse)s
	
# # 	#     WHERE IFNULL(b.actual_qty, 0) > 0
	
# # 	# """, {"warehouse": warehouse}, as_dict=True)

# #     sku_details = frappe.db.sql("""
# #         SELECT
# #             s.name AS sku_name,
# #             s.name AS sku,
# #             s.product,
# #             s.sku_master,
# #             1 AS qty,
# #             s.selling_price,
# #             s.gross_weight,
# #             s.net_weight,
# #             s.huid,
# #             s.d_no,
# #             s.image

# #         FROM `tabSKU` s

# #         WHERE s.warehouse = %(warehouse)s

# #     """, {"warehouse": warehouse}, as_dict=True)

# #     for item in sku_details:

# #         # ✅ Image URL + Name
# #         image_path = item.get("image")
# #         if image_path:
# #             item["image_url"] = site_url + image_path
# #             item["image_name"] = image_path.split("/")[-1]
# #         else:
# #             item["image_url"] = None
# #             item["image_name"] = None

# #         # ✅ QR Code (safe)
# #         qr_data = item.get("sku") or item.get("sku_name")

# #         if QR_AVAILABLE and qr_data:
# #             try:
# #                 qr = qrcode.make(qr_data)
# #                 buffer = BytesIO()
# #                 qr.save(buffer, format="PNG")

# #                 qr_base64 = base64.b64encode(buffer.getvalue()).decode()
# #                 item["qr_code"] = f"data:image/png;base64,{qr_base64}"
# #             except Exception:
# #                 item["qr_code"] = None
# #         else:
# #             item["qr_code"] = None

# #     return {
# #         "sku_details": sku_details
# #     }


# # @frappe.whitelist(allow_guest=True)
# # def get_location_master_list():

# #     locations = frappe.get_all(
# #         "Warehouse",
# #         filters={"custom_include_in_rfid": 1},
# #         fields=["name"]
# #     )

# #     # Return only list of names
# #     return [loc["name"] for loc in locations]


# # #working before QR
# # import frappe
# # import base64
# # from io import BytesIO

# # # ✅ Safe import (prevents crash if qrcode not installed)
# # try:
# #     import qrcode
# #     QR_AVAILABLE = True
# # except ImportError:
# #     QR_AVAILABLE = False

# # @frappe.whitelist(allow_guest=True)
# # def get_sku_details(warehouse=None):

# #     if not warehouse:
# #         frappe.throw("Warehouse is required")

# #     site_url = frappe.utils.get_url()

# #     sku_details = frappe.db.sql("""
# #         SELECT
# #             s.name AS sku_name,
# #             s.name AS sku,
# #             s.product,
# #             s.sku_master,
# #             s.breakup_ref,
# #             s.old_sku_ref,
# #             1 AS qty,
# #             s.selling_price,
# #             s.gross_weight,
# #             s.net_weight,
# #             s.huid,
# #             s.d_no,
# #             s.image

# #         FROM `tabSKU` s

# #         WHERE s.warehouse = %(warehouse)s

# #     """, {"warehouse": warehouse}, as_dict=True)

# #     for item in sku_details:
# #         breakup_rows = frappe.get_all(
# #             "SKU Breakup",
# #             filters={
# #                 "sku_master": item.get("sku_master"),
# #                 "breakup_ref": item.get("breakup_ref")
# #             },
# #             fields=[
# #                 "attribute_type",
# #                 "attribute_value",
# #                 "weight",
# #                 "price",
# #                 "unit"
# #             ],
# #             order_by="creation asc"
# #         )

# #         item["breakup"] = breakup_rows or []

# #         # ✅ Image URL + Name
# #         image_path = item.get("image")
# #         if image_path:
# #             item["image_url"] = site_url + image_path
# #             item["image_name"] = image_path.split("/")[-1]
# #         else:
# #             item["image_url"] = None
# #             item["image_name"] = None

# #         # ✅ QR Code (safe)
# #         qr_data = item.get("sku") or item.get("sku_name")

# #         if QR_AVAILABLE and qr_data:
# #             try:
# #                 qr = qrcode.make(qr_data)
# #                 buffer = BytesIO()
# #                 qr.save(buffer, format="PNG")

# #                 qr_base64 = base64.b64encode(buffer.getvalue()).decode()
# #                 item["qr_code"] = f"data:image/png;base64,{qr_base64}"
# #             except Exception:
# #                 item["qr_code"] = None
# #         else:
# #             item["qr_code"] = None

# #     return {
# #         "sku_details": sku_details
# #     }


# # @frappe.whitelist(allow_guest=True)
# # def get_location_master_list():

# #     locations = frappe.get_all(
# #         "Warehouse",
# #         filters={"custom_include_in_rfid": 1},
# #         fields=["name"]
# #     )

# #     # Return only list of names
# #     return [loc["name"] for loc in locations]


# import frappe
# import base64
# from io import BytesIO
# from urllib.parse import quote
# from urllib.parse import unquote

# # ✅ Safe import (prevents crash if qrcode not installed)
# try:
#     import qrcode
#     QR_AVAILABLE = True
# except ImportError:
#     QR_AVAILABLE = False


# # =========================================================
# # Reusable SKU Data Builder
# # =========================================================
# def _get_sku_details_data(warehouse=None, sku=None):

#     site_url = frappe.utils.get_url()

#     # =========================================================
#     # Dynamic Conditions
#     # =========================================================
#     conditions = []
#     filters = {}

#     if warehouse:
#         conditions.append("s.warehouse = %(warehouse)s")
#         filters["warehouse"] = warehouse

#     if sku:
#         conditions.append("s.name = %(sku)s")
#         filters["sku"] = sku

#     where_clause = " AND ".join(conditions)

#     # =========================================================
#     # Main SKU Query
#     # =========================================================
#     sku_details = frappe.db.sql(f"""
#         SELECT
#             s.name AS sku_name,
#             s.name AS sku,
#             s.product,
#             s.sku_master,
#             s.breakup_ref,
#             s.old_sku_ref,
#             s.image_url,
#             1 AS qty,
#             s.selling_price,
#             s.gross_weight,
#             s.net_weight,
#             s.huid,
#             s.d_no

#         FROM `tabSKU` s

#         WHERE {where_clause}
#     """, filters, as_dict=True)

#     # =========================================================
#     # Process Each SKU
#     # =========================================================
#     for item in sku_details:

#         # =====================================================
#         # Public QR URL
#         # =====================================================
#         qr_url = (
#             f"{site_url}/sku_qr"
#             f"?sku={item.get('sku')}"
#         )

#         item["qr_url"] = qr_url

#         # =====================================================
#         # Breakup Data
#         # =====================================================
#         # breakup_rows = frappe.get_all(
#         #     "SKU Breakup",
#         #     filters={
#         #         "sku_master": item.get("sku_master"),
#         #         "breakup_ref": item.get("breakup_ref")
#         #     },
#         #     fields=[
#         #         "attribute_type",
#         #         "attribute_value",
#         #         "weight",
#         #         "price",
#         #         "unit"
#         #     ],
#         #     order_by="creation asc"
#         # )

#         # =====================================================
#         # Common Attribute Rows
#         # =====================================================
#         common_rows = frappe.get_all(
#             "SKU Breakup",
#             filters={
#                 "sku_master": item.get("sku_master"),
#                 "attribute_type": ["in", [
#                     "PURITY",
#                     "PRODUCT_TYPE",
#                     "DESIGN",
#                     "TARGET",
#                     "VISUAL",
#                     "COLLECTION"
#                 ]]
#             },
#             fields=[
#                 "attribute_type",
#                 "attribute_value",
#                 "weight",
#                 "price",
#                 "unit"
#             ],
#             order_by="creation asc"
#         )

#         # =====================================================
#         # Breakup Specific Rows
#         # =====================================================
#         specific_rows = frappe.get_all(
#             "SKU Breakup",
#             filters={
#                 "sku_master": item.get("sku_master"),
#                 "breakup_ref": item.get("breakup_ref")
#             },
#             fields=[
#                 "attribute_type",
#                 "attribute_value",
#                 "weight",
#                 "price",
#                 "unit"
#             ],
#             order_by="creation asc"
#         )

#         # =====================================================
#         # Merge Both
#         # =====================================================
#         breakup_rows = common_rows + specific_rows


#         # Exclude empty breakup rows from RFID payload; rows with weight, price, or unit stay.
#         breakup_rows = [
#             row for row in breakup_rows
#             if not (
#                 frappe.utils.flt(row.get("weight")) == 0
#                 and frappe.utils.flt(row.get("price")) == 0
#                 and not (row.get("unit") or "").strip()
#             )
#         ]

#         # item["breakup"] = breakup_rows or []
#         # =====================================================
#         # Unit Short Forms
#         # =====================================================
#         UNIT_MAP = {
#             "Carat": "cts",
#             "Gram": "gm"
#         }

#         for row in breakup_rows:
#             row["unit"] = UNIT_MAP.get(
#                 row.get("unit"),
#                 row.get("unit")
#             )

#         item["breakup"] = breakup_rows or []

#         # =====================================================
#         # Image URL + Name
#         # =====================================================
#         image_path = item.get("image_url")

#         if image_path:

#             # Convert relative path to full URL
#             if image_path.startswith("/"):
#                 full_image_url = site_url + image_path
#             else:
#                 full_image_url = image_path

#             item["image_url"] = full_image_url
#             item["image_name"] = image_path.split("/")[-1]

#         else:
#             item["image_url"] = None
#             item["image_name"] = None

#         # =====================================================
#         # QR Code Generation
#         # =====================================================
#         item["qr_code"] = None

#         if QR_AVAILABLE and qr_url:

#             try:
#                 qr = qrcode.make(qr_url)

#                 buffer = BytesIO()
#                 qr.save(buffer, format="PNG")

#                 qr_base64 = base64.b64encode(
#                     buffer.getvalue()
#                 ).decode()

#                 item["qr_code"] = (
#                     f"data:image/png;base64,{qr_base64}"
#                 )

#             except Exception:
#                 frappe.log_error(
#                     title="QR Code Generation Failed",
#                     message=frappe.get_traceback()
#                 )

#                 item["qr_code"] = None

#     return sku_details


# # =========================================================
# # Public API
# # =========================================================
# @frappe.whitelist(allow_guest=True)
# def get_sku_details(warehouse=None, sku=None):

#     # =========================================================
#     # Validation
#     # =========================================================
#     if warehouse:
#         warehouse = unquote(warehouse)

#     if not warehouse and not sku:
#         frappe.throw("Warehouse or SKU is required")

#     sku_details = _get_sku_details_data(
#         warehouse=warehouse,
#         sku=sku
#     )

#     return {
#         "sku_details": sku_details
#     }


# # =========================================================
# # Warehouse List API
# # =========================================================
# @frappe.whitelist(allow_guest=True)
# def get_location_master_list():

#     locations = frappe.get_all(
#         "Warehouse",
#         filters={
#             "custom_include_in_rfid": 1
#         },
#         fields=["name"],
#         order_by="name asc"
#     )

#     # return [loc["name"] for loc in locations]

#     return [
#         {
#             "warehouse_name": loc["name"],
#             "warehouse_encoded": quote(loc["name"])
#         }
#         for loc in locations
#     ]

# # =========================================================
# # Debug QR Library Check
# # =========================================================
# @frappe.whitelist(allow_guest=True)
# def debug_qr_install():

#     result = {}

#     # =====================================================
#     # Check qrcode
#     # =====================================================
#     try:
#         import qrcode

#         result["qrcode_import"] = "SUCCESS"
#         result["qrcode_version"] = getattr(qrcode, "__version__", "UNKNOWN")

#     except Exception as e:
#         result["qrcode_import"] = str(e)

#     # =====================================================
#     # Check PIL
#     # =====================================================
#     try:
#         from PIL import Image

#         result["pillow_import"] = "SUCCESS"

#     except Exception as e:
#         result["pillow_import"] = str(e)

#     # =====================================================
#     # Try QR Generation
#     # =====================================================
#     try:
#         import qrcode
#         from io import BytesIO

#         qr = qrcode.make("TEST QR")

#         buffer = BytesIO()

#         qr.save(buffer, format="PNG")

#         result["qr_generation"] = "SUCCESS"

#     except Exception as e:
#         result["qr_generation"] = str(e)

#     return result
