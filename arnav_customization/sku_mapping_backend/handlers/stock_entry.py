import frappe
from arnav_customization.sku_mapping_backend.sku_service import get_sku_data

def process(doc, method):

    for row in doc.items:

        if not row.custom_sku:
            continue

        sku = get_sku_data(row.custom_sku)

        row.item_code = sku.product
        row.qty = sku.gross_weight
        row.batch_no = sku.batch_no or row.custom_sku

        row.basic_rate = sku.cost_price
        row.valuation_rate = sku.valuation_rate

        if not row.s_warehouse and not row.t_warehouse:
            row.t_warehouse = sku.warehouse

def material_transfer_qty_handler(doc, method):

    # only for material transfer
    if doc.purpose != "Material Transfer":
        return

    # dynamic switch
    if not doc.custom_use_qty_mode:
        return

    for row in doc.items:

        # skip empty rows
        if not row.custom_gross_weight:
            continue

        # preserve original gross weight
        row.custom_weight = row.qty

        # IMPORTANT:
        # actual stock qty becomes custom qty
        row.qty = float(row.custom_gross_weight)

        # avoid transfer qty mismatch
        row.transfer_qty = float(row.custom_gross_weight)