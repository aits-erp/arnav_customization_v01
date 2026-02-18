import frappe

@frappe.whitelist()
def create_sku_master(
    product,
    sku,
    qty=None,
    cost_price=None,
    selling_price=None,
    image=None,
    gross_weight=None,
    net_weight=None,
    breakup=None
):

    # ⭐ Parent Doc Create
    doc = frappe.new_doc("SKU")

    # ⭐ Child Table Row Add
    doc.append("sku_details", {
        "product": product,
        "sku": sku,
        "qty": qty,
        "cost_price": cost_price,
        "selling_price": selling_price,
        "image": image,
        "gross_weight": gross_weight,
        "net_weight": net_weight,
        "breakup": breakup
    })

    doc.insert(ignore_permissions=True)
    doc.submit()

    return {
        "status": "success",
        "name": doc.name
    }
