import frappe
from arnav_customization.arnav_customization.doctype.sku_master.sku_master import get_breakup_rows_for_reference

@frappe.whitelist()
def get_sku_data(sku):

    if not sku:
        return {}

    sku_doc = frappe.get_doc("SKU", sku)
    breakup = get_breakup_rows_for_reference(
        sku_doc.sku_master,
        sku_doc.breakup_ref
    )

    return {
        "item_code": sku_doc.product,
        "batch_no": sku_doc.batch_no or sku_doc.name,
        "gross_weight": sku_doc.gross_weight,
        "net_weight": sku_doc.net_weight,
        "rate": sku_doc.selling_price,
        "cost_price": sku_doc.cost_price,
        "valuation_rate": sku_doc.valuation_rate,
        "hsn": sku_doc.hsn,
        "metal": sku_doc.metal,
        "warehouse": sku_doc.warehouse,
        "qty": sku_doc.qty,
        "d_no": sku_doc.d_no,
        "huid": sku_doc.huid,
        "breakup": breakup
    }
