import frappe

from arnav_customization.api import _get_sku_details_data


def get_context(context):

    # =========================================================
    # Get SKU from URL
    # Example:
    # /sku_qr?sku=SKU-001
    # =========================================================
    sku = frappe.form_dict.get("sku")

    context.no_cache = 1

    # =========================================================
    # Validation
    # =========================================================
    if not sku:
        context.message = "SKU not found"
        context.item = None
        return context

    # =========================================================
    # Fetch SKU Data
    # =========================================================
    sku_data = _get_sku_details_data(sku=sku)

    # =========================================================
    # No Data Found
    # =========================================================
    if not sku_data:
        context.message = "No SKU data found"
        context.item = None
        return context

    # =========================================================
    # Send First Item to HTML
    # =========================================================
    context.item = sku_data[0]

    return context