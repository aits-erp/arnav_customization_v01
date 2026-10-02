# from arnav_customization.sku_mapping_backend.sku_service import get_sku_data

# def process(doc, method):

#     for row in doc.items:

#         if not row.custom_sku:
#             continue

#         sku = get_sku_data(row.custom_sku)
#         if not sku:
#             continue

#         row.item_code = sku.product
#         row.qty = sku.gross_weight
#         # row.qty = sku.qty
#         row.custom_net_weight = sku.net_weight
#         row.custom_quantity = sku.qty
#         row.rate = sku.selling_price
#         row.gst_hsn_code = sku.hsn
#         row.warehouse = sku.warehouse
#         row.batch_no = sku.batch_no or row.custom_sku


import frappe
from frappe.utils import flt

from arnav_customization.sku_mapping_backend.sku_service import get_sku_data


def process(doc, method):

    for row in doc.items:

        if not row.custom_sku:
            continue

        sku = get_sku_data(row.custom_sku)

        if not sku:
            continue

        # ==========================================
        # ITEM
        # ==========================================

        row.item_code = sku.product

        # ==========================================
        # QUANTITY
        # ==========================================
        #
        # Normal Sales Invoice:
        #     use SKU quantity
        #
        # Sales Return:
        #     DO NOT overwrite qty.
        #     POS mapping already gives negative qty.
        #
        if not doc.is_return:
            row.qty = sku.qty

        # ==========================================
        # WEIGHT / SKU INFORMATION
        # ==========================================

        row.custom_gross_weight = sku.gross_weight
        row.custom_net_weight = sku.net_weight
        row.custom_quantity = sku.qty

        # ==========================================
        # RATE
        # ==========================================
        #
        # Normal Sales Invoice:
        #     use current SKU selling price
        #
        # Sales Return:
        #     use original POS transaction rate
        #
        if not doc.is_return:
            row.rate = sku.selling_price

        # ==========================================
        # OTHER FIELDS
        # ==========================================

        row.gst_hsn_code = sku.hsn
        row.warehouse = sku.warehouse
        row.batch_no = sku.batch_no or row.custom_sku

    restore_pos_return_pricing(doc)


def restore_pos_return_pricing(doc):
    """Keep POS returns tied to the recorded POS amount, not today's Item Price."""
    if not (doc.is_return and doc.custom_pos):
        return

    pos = frappe.get_doc("POS", doc.custom_pos)
    pricing_by_sku = {row.sku: row for row in pos.sku_details if row.sku}
    changed = False

    for item in doc.items:
        source = pricing_by_sku.get(item.custom_sku)
        if not source:
            continue

        source_qty = flt(source.qty) or 1
        gross_rate = flt(source.price)
        unit_discount = flt(source.discount) / source_qty
        effective_rate = flt(source.final_amount) / source_qty

        # Price List Rate is retained only as the reference/MRP.  The
        # transaction Rate is the POS's actual discounted unit price.
        item.custom_custom_rate = gross_rate
        item.price_list_rate = gross_rate
        item.rate_with_margin = gross_rate
        item.discount_amount = unit_discount
        item.discount_percentage = (unit_discount / gross_rate * 100) if gross_rate else 0
        item.rate = effective_rate
        changed = True

    if changed:
        doc.calculate_taxes_and_totals()
