import frappe
from arnav_customization.sku_mapping_backend.sku_service import get_sku_data


def process(doc, method):

    for row in doc.items:

        if not row.custom_sku:
            continue

        sku = get_sku_data(row.custom_sku)

        row.item_code = sku.product

        # DEFAULT UI DISPLAY
        # show gross weight in qty initially
        row.qty = float(sku.gross_weight or 0)

        # preserve gross weight separately
        row.custom_gross_weight = float(sku.gross_weight or 0)

        # IMPORTANT
        row.serial_and_batch_bundle = None

        row.batch_no = sku.batch_no or row.custom_sku

        row.basic_rate = sku.cost_price
        row.valuation_rate = sku.valuation_rate

        if not row.s_warehouse and not row.t_warehouse:
            row.t_warehouse = sku.warehouse


def material_transfer_qty_handler(doc, method):

    # only for transfer / issue
    if doc.purpose not in ["Material Transfer", "Material Issue"]:
        return

    # checkbox disabled = normal ERP behavior
    if not doc.custom_use_qty_mode:
        return

    for row in doc.items:

        # skip invalid rows
        if not row.item_code:
            continue

        # preserve gross weight before switching
        if row.qty and not row.custom_gross_weight:
            row.custom_gross_weight = row.qty

        # actual stock movement qty
        actual_qty = float(row.custom_gross_weight or 1)

        # IMPORTANT:
        # ERP stock movement fields
        row.qty = actual_qty
        row.transfer_qty = actual_qty

        # prevent bundle validation issue
        row.serial_and_batch_bundle = None


# # def material_transfer_qty_handler(doc, method):

# #     # only for material transfer
# #     if doc.purpose != "Material Transfer" or doc.purpose != "Material Issue":
# #         return

# #     # dynamic switch
# #     if not doc.custom_use_qty_mode:
# #         return

# #     for row in doc.items:

# #         # skip empty rows
# #         if not row.custom_gross_weight:
# #             continue

# #         # preserve original gross weight
# #         row.custom_weight = row.qty

# #         # IMPORTANT:
# #         # actual stock qty becomes custom qty
# #         row.qty = float(row.custom_gross_weight)

# #         # avoid transfer qty mismatch
# #         row.transfer_qty = float(row.custom_gross_weight)

