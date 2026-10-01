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

        row.item_code = sku.product

        # Quantity
        # Normal Sales Invoice -> SKU quantity
        # Sales Return -> preserve the negative quantity
        # already created by make_credit_note()
        if not doc.is_return:
            row.qty = sku.qty

        # Weight
        row.custom_gross_weight = sku.gross_weight
        row.custom_net_weight = sku.net_weight
        row.custom_quantity = sku.qty

        # Rate
        # Normal Sales Invoice -> current SKU selling price
        # Sales Return -> preserve the original POS price
        if not doc.is_return:
            row.rate = sku.selling_price

        row.gst_hsn_code = sku.hsn
        row.warehouse = sku.warehouse
        row.batch_no = sku.batch_no or row.custom_sku