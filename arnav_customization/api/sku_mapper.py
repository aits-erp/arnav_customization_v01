import frappe

@frappe.whitelist()
def get_sku_data(sku):

    if not sku:
        return {}

    sku_doc = frappe.get_doc("SKU", sku)

    return {
        "item_code": sku_doc.product,
        "batch_no": sku_doc.batch_no or sku_doc.name,
        "qty": sku_doc.gross_weight,   # client rule: qty = gross_weight
        "rate": sku_doc.selling_price,
        "valuation_rate": sku_doc.valuation_rate,
        "hsn": sku_doc.hsn,
        "warehouse": sku_doc.warehouse
    }