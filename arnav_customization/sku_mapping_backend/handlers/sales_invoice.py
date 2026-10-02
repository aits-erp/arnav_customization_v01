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
