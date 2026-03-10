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