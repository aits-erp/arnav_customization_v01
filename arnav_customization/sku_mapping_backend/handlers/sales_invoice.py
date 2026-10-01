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

    # =====================================================
    # SALES RETURN PRICE FIX
    # =====================================================
    #
    # ERPNext standard pricing can replace the original
    # POS rate with the current Standard Selling price.
    #
    # For a POS return, restore the historical transaction
    # rate from custom_custom_rate.
    #
    if doc.is_return:

        for row in doc.items:

            if not row.custom_custom_rate:
                continue

            original_rate = row.custom_custom_rate

            # Restore original POS rate
            row.rate = original_rate

            # Do not allow current price-list rate to replace it
            row.price_list_rate = original_rate

            # POS transaction already contains the historical
            # rate, so don't apply a new selling-price discount.
            row.discount_percentage = 0
            row.discount_amount = 0

            # Recalculate item amount
            row.amount = row.qty * row.rate

            # Stock UOM rate
            conversion_factor = row.conversion_factor or 1

            row.stock_uom_rate = row.rate / conversion_factor

            # Net values
            row.net_rate = row.rate
            row.net_amount = row.amount

            row.base_rate = row.rate * (doc.conversion_rate or 1)
            row.base_amount = row.amount * (doc.conversion_rate or 1)

            row.base_net_rate = row.net_rate * (doc.conversion_rate or 1)
            row.base_net_amount = row.net_amount * (doc.conversion_rate or 1)

        # Recalculate taxes and totals after restoring the
        # original POS rate.
        doc.calculate_taxes_and_totals()