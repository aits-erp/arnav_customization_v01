from arnav_customization.sku_mapping_backend.sku_service import get_sku_data

def process(doc, method):

    for row in doc.items:

        if not row.custom_sku:
            continue

        sku = get_sku_data(row.custom_sku)
        if not sku:
            continue

        row.item_code = sku.product
        row.qty = sku.gross_weight
        row.custom_net_weight = sku.net_weight
        row.custom_quantity = sku.qty
        row.rate = sku.selling_price
        row.gst_hsn_code = sku.hsn
        row.warehouse = sku.warehouse
        row.batch_no = sku.batch_no or row.custom_sku